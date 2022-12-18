from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import psycopg2.extras
import re
from flask import Flask, render_template, url_for, request, flash, session, redirect
from config import host, user, password, db_name
import cli
from datetime import date
import numpy
import os
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = 'mariozurab'


try:
    conn = psycopg2.connect(
        database=db_name,
        user=user,
        password=password,
        host=host)
except:
    print('no connection')


#--------------------Заготовка для добавления фотографий к объявлениям-------------------
UPLOAD_FOLDER = 'static/image/'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
#----------------------------------------------------------------------------------------


def create_db():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute(cli.create_database())


@app.route('/')
@app.route('/home')
def index():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute(
        "SELECT id_product, product_name, cost, description, id_user, id_category FROM product;")
    item = cursor.fetchall()

    cursor.execute(
        "SELECT id_category, category_name FROM category;")
    categorys = cursor.fetchall()

    return render_template("index.html", item=item, categorys=categorys)


@app.route('/category/<int:id_categ>')
def showCategory(id_categ):
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute(
        "SELECT id_product, product_name, cost, description, id_user, id_category FROM product WHERE id_category = %s;",
        (id_categ,))
    show_category = cursor.fetchall()
    return render_template("categorys.html", show_category=show_category)


@app.route('/item/<int:id_item>')
def showItem(id_item):
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute(
        "SELECT id_product, product_name, cost, description, id_user, id_category FROM product WHERE id_product = %s;",
        (id_item,))
    show_item = cursor.fetchall()

    cursor.execute(
        "SELECT id_user, name, telephone, id_city FROM userr WHERE id_user IN (SELECT id_user FROM product WHERE id_product = %s);",
        (id_item,))
    show_profile = cursor.fetchall()

    # Вывод названия города пользователя
    cursor.execute(
        "SELECT city_name FROM city WHERE id_city IN (SELECT id_city FROM userr WHERE id_user IN (SELECT id_user FROM product WHERE id_product = %s));",
        (id_item,))
    user_city = cursor.fetchall()

    # Рейтинг продавца
    cursor.execute(
        'SELECT mark FROM estimation WHERE id_profile IN (SELECT id_user FROM product WHERE id_product = %s)',
        (id_item,))
    mark_info = cursor.fetchall()
    rating = round(numpy.average(mark_info), 1)

    return render_template("showitem.html", show_item=show_item, show_profile=show_profile, user_city=user_city,
                           rating=rating)


@app.route('/register', methods=['GET', 'POST'])
def register():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # Проверка, существуют ли запросы на публикацию "имя пользователя"
    # и "пароль" (форма, отправленная пользователем)
    if request.method == 'POST' and 'user_login' in request.form and 'password' in request.form:
        # Создавайте переменные для легкого доступа
        user_name = request.form['user_name']
        user_login = request.form['user_login']
        user_mail = request.form['user_mail']
        password = request.form['password']
        _hashed_password = generate_password_hash(password)

        # Проверьте, существует ли учетная запись, используя PostgreSQL
        cursor.execute(
            'SELECT * FROM userr WHERE login = %s', (user_login,))
        account = cursor.fetchone()

        # Если учетная запись существует, покажите проверки на ошибку и валидацию
        if account:
            flash('Учетная запись уже существует!')
        elif not re.match(r'[A-Za-z0-9]+', user_login):
            flash('Имя пользователя должно содержать только символы и цифры!')
        elif not user_login or not password or not user_name:
            flash('Пожалуйста, заполните форму!')
        else:
            # Учетная запись не существует, и данные формы действительны, теперь заносится
            # новая учетная запись в таблицу пользователей
            cursor.execute(
                "INSERT INTO userr (name, login, e_mail, password) VALUES (%s,%s,%s,%s)",
                           (user_name, user_login, user_mail, _hashed_password))
            conn.commit()
            return redirect(url_for('login'))

    elif request.method == 'POST':
        flash('Please fill out the form!')

    return render_template("register.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # Проверка, существуют ли запросы на публикацию "имя пользователя" и
    # "пароль" (форма, отправленная пользователем)
    if request.method == 'POST' and 'user_login' in request.form and 'password' in request.form:
        user_login = request.form['user_login']
        password = request.form['password']

        cursor.execute(
            'SELECT * FROM userr WHERE login = %s', (user_login,))
        account = cursor.fetchone()
        if account:
            password_rs = account['password']
            # Если учетная запись существует в таблице пользователей в базе данных out
            if check_password_hash(password_rs, password):
                # Создайте данные сеанса, мы можем получить доступ к
                # этим данным другими маршрутами
                session['loggedin'] = True
                session['user_login'] = account['login']
                session['user_name'] = account['name']
                session['id_user'] = account['id_user']
                # Перенаправление на страницу профиля
                return redirect(url_for('profile'))
            else:
                # Учетная запись не существует или имя пользователя/пароль неверны
                flash('Неправильное имя пользователя / пароль')
        else:
            # Учетная запись не существует или имя пользователя/пароль неверны
            flash('Неправильное имя пользователя / пароль')

    elif request.method == 'POST':
        flash('Пожалуйста, заполните форму!')

    return render_template("login.html")


@app.route('/logout')
def logout():
    # Dыход пользователя из системы
    session.clear()
    return redirect(url_for('login'))


@app.route('/profile')
def profile():
    if 'loggedin' in session:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute('SELECT * FROM userr WHERE login = %s', [session['user_login']])
        account = cursor.fetchone()

        # Вывод своих объявлений в профиле
        cursor.execute(
            "SELECT id_product, product_name, cost, description, id_user, id_category FROM product WHERE id_user=%s;", [session['id_user']])
        adsitems = cursor.fetchall()

        # Вывод названия города пользователя
        cursor.execute("SELECT city_name FROM city WHERE id_city IN (SELECT id_city FROM userr WHERE id_user = %s)", [session['id_user']])
        user_city = cursor.fetchall()
        # Show the profile page with account info

        # Рейтинг продавца
        cursor.execute(
            'SELECT mark FROM estimation WHERE id_profile = %s;',
            [session['id_user']])
        mark_info = cursor.fetchall()
        rating = round(numpy.average(mark_info), 1)
        return render_template('profile.html', account=account, adsitems=adsitems, user_city=user_city, rating=rating)
    return redirect(url_for('login'))


@app.route('/edit_profile/<int:id_editprof>', methods=['GET', 'POST'])
def editProfile(id_editprof):
    if 'loggedin' in session:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute('SELECT id_user, name, e_mail, telephone FROM userr WHERE id_user = %s',
                       [id_editprof])
        profile_info = cursor.fetchall()

        cursor.execute("SELECT id_city, city_name FROM city;")
        list_city = cursor.fetchall()
        if request.method == 'POST':
            name = request.form['name']
            e_mail = request.form['e_mail']
            telephone = request.form['telephone']
            id_city = request.form['city']

            if not name or not e_mail:
                flash('Пожалуйста, заполните форму!', category='error')
            elif len(name) > 50:
                flash('Максимальное количесво символов 50', category='error')
            elif len(e_mail) > 50:
                flash('Максимальное количесво символов 50', category='error')
            else:
                cursor.execute(
                    "UPDATE userr SET name = %s, e_mail = %s, telephone = %s, id_city = %s WHERE id_user = %s",
                    (name, e_mail, telephone, id_city, id_editprof))
                conn.commit()
                flash('Изменения сохранены!', category='success')
                return redirect(url_for('profile', id_editprof=session['user_login']))
        return render_template('editprofile.html', profile_info=profile_info, list_city=list_city)
    return redirect(url_for('login'))


@app.route('/additem', methods=['GET', 'POST'])
def additem():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT id_category, category_name FROM category;")
    list_category = cursor.fetchall()

    if 'loggedin' in session:
        if request.method == 'POST':
            product_name = request.form['product_name']
            description = request.form['description']
            cost = request.form['cost']
            id_category = request.form['category']


            if not product_name or not description or not cost:
                flash('Пожалуйста заполните форму!', category='error')
            if len(product_name) > 100:
                flash('Максимальное количество символов 100', category='error')
            elif len(description) > 1000:
                flash('Максимальное количество символов 1000', category='error')
            else:
                cursor.execute(
                    "INSERT INTO product (product_name, description, cost, id_user, id_category) VALUES (%s,%s,%s,%s,%s)",
                               (product_name, description, cost, session['id_user'], id_category))
                conn.commit()

                flash('Объявление добавлено!', category='success')
                return redirect(url_for('profile', id=session['user_login']))
        return render_template('additem.html', list_category=list_category)
    return redirect(url_for('login'))


@app.route('/edit_item/<int:id_edititem>', methods=['GET', 'POST'])
def editItem(id_edititem):
    if 'loggedin' in session:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("SELECT id_product, product_name, cost, description, id_user, id_category FROM product WHERE id_product = %s;",
                       [id_edititem])
        item_info = cursor.fetchall()
        if request.method == 'POST':
            product_name = request.form['product_name']
            cost = request.form['cost']
            description = request.form['description']

            if not product_name or not description:
                flash('Пожалуйста заполните форму!', category='error')
            if len(product_name) > 100:
                flash('Максимальное количество символов 100', category='error')
            elif len(description) > 1000:
                flash('Максимальное количество символов 1000', category='error')
            else:
                cursor.execute(
                    "UPDATE product SET product_name = %s, cost = %s, description = %s  WHERE id_product = %s",
                    (product_name, cost, description, id_edititem))
                conn.commit()
                flash('Объявление отредактированно!', category='success')
                return redirect(url_for('profile', id_edititem=item_info))
        return render_template('edititem.html', item_info=item_info)
    return redirect(url_for('login'))


@app.route('/deleteitem/<int:id_deleteitem>', methods=['GET', 'POST'])
def deleteItem(id_deleteitem):
    if request.method == 'POST':
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        if (request.form.get('yes', None)):
            cursor.execute(
                "DELETE FROM product WHERE id_product = %s",
                [id_deleteitem])
            conn.commit()
            return redirect(url_for('profile'))
    return render_template('deleteitem.html')


# просмотр профиль пользователя (покупатель/продовец)
@app.route('/showprofile/<int:id_profile>')
def showProfile(id_profile):
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Вывод информации о пользователе
    cursor.execute('SELECT * FROM userr WHERE id_user = %s', (id_profile,))
    account = cursor.fetchone()

    # Вывод объявлений пользователя в профиле
    cursor.execute(
        "SELECT id_product, product_name, cost, description, id_user, id_category FROM product WHERE id_user=%s;",
        (id_profile,))
    adsitems = cursor.fetchall()

    # Вывод названия города пользователя
    cursor.execute("SELECT city_name FROM city WHERE id_city IN (SELECT id_city FROM userr WHERE id_user = %s)",
                   (id_profile,))
    user_city = cursor.fetchall()

    # Айди для перехода в форму для отзыва
    cursor.execute(
        "SELECT id_product, product_name, cost, description, id_user, id_category FROM product WHERE id_user=%s LIMIT 1;",
        (id_profile,))
    profile_id_user = cursor.fetchall()

    # Отзывы пользователя оставленные другими пользователями
    cursor.execute('SELECT id_esti, id_profile, mark, text, date, id_user FROM estimation WHERE id_profile = %s',
                   (id_profile,))
    estimation_info = cursor.fetchall()

    # Имя пользователя оставивший отзыв (айди для перенаправления на профиль пользователя, оставивший отзыв)
    cursor.execute('SELECT id_user, name FROM userr WHERE id_user IN (SELECT id_user FROM estimation WHERE id_profile = %s)',
                   (id_profile,))
    estimation_info_user = cursor.fetchall()

    # Рейтинг продавца
    cursor.execute('SELECT  mark FROM estimation WHERE id_profile = %s',
                   (id_profile,))
    mark_info = cursor.fetchall()
    rating = round(numpy.average(mark_info), 1)

    return render_template("showprofile.html",
                           account=account, adsitems=adsitems, user_city=user_city,
                           profile_id_user=profile_id_user, estimation_info=estimation_info,
                           estimation_info_user=estimation_info_user, id_profile=id_profile,
                           id_usersee=session['id_user'], rating=rating)


# Отзыв
@app.route('/leavereview/<int:id_profiluser>', methods=['GET', 'POST'])
def leaveReview(id_profiluser):
    if 'loggedin' in session:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        if request.method == 'POST':
            mark = request.form['mark']
            text = request.form['text']
            date_info = date.today()

            if not text or not text:
                flash('Пожалуйста заполните форму!', category='error')
            elif len(text) > 500:
                flash('Максимальное количество символов 500', category='error')
            else:
                cursor.execute(
                    "INSERT INTO estimation (id_profile, mark, text, date, id_user) VALUES (%s,%s,%s,%s,%s)",
                    (id_profiluser, mark, text, date_info, session['id_user']))
                conn.commit()
                flash('Отзыв опубликован!', category='success')
                return redirect(url_for('showProfile', id_profile=id_profiluser))
        return render_template('leavereview.html', id_profiluser=id_profiluser)
    return redirect(url_for('login'))


# начало функционала для администратора-модератора
# авторизация для администратора
@app.route('/admin', methods=['GET', 'POST'])
def loginadmin():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # Проверка, существуют ли запросы на публикацию "имя пользователя" и
    # "пароль" (форма, отправленная пользователем)
    if request.method == 'POST' and 'user_login' in request.form and 'password' in request.form:
        user_login = request.form['user_login']
        password = request.form['password']

        cursor.execute(
            'SELECT * FROM admin WHERE login = %s', (user_login,))
        account = cursor.fetchone()
        if account:
            password_rs = account['password']
            # Если учетная запись существует в таблице пользователей в базе данных out
            if password_rs == password:
                # Создайте данные сеанса, мы можем получить доступ к
                # этим данным другими маршрутами
                session['loggedinadmin'] = True
                session['admin_login'] = account['login']
                session['id_admin'] = account['id_admin']
                # Перенаправление на страницу просмотра объявлений пользователей
                return redirect(url_for('itemadmin'))
            else:
                flash('Неправильный логин / пароль')
        else:
            flash('Неправильный логин / пароль')

    elif request.method == 'POST':
        flash('Пожалуйста, заполните форму!')

    return render_template("loginadmin.html")


# выход из сесии администратора
@app.route('/logoutadmin')
def logoutAdmin():
    # Dыход пользователя из системы
    session.clear()
    return redirect(url_for('index'))


# список всех объявлений пользователей (для администратора-модератора)
@app.route('/itemadmin')
def itemadmin():
    if 'loggedinadmin' in session:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute(
            "SELECT id_product, product_name, cost, description, id_user, id_category FROM product;")
        item = cursor.fetchall()

        return render_template("itemadmin.html", item=item)
    return render_template("loginadmin.html")


# переход на страницу уонкретного объявления (для администратора-модератора)
@app.route('/itemadmin/<int:id_item>')
def showItemAdmin(id_item):
    if 'loggedinadmin' in session:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute(
            "SELECT id_product, product_name, cost, description, id_user, id_category FROM product WHERE id_product = %s;",
            (id_item,))
        show_item = cursor.fetchall()
        return render_template("showitemadmin.html", show_item=show_item)
    return render_template("loginadmin.html")


# список всех пользователей
@app.route('/adminseeuser')
def adminSeeUser():
    if 'loggedinadmin' in session:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute(
            "SELECT id_user, name, login, e_mail, telephone FROM userr;")
        user = cursor.fetchall()
        return render_template("adminseeuser.html", user=user)
    return render_template("loginadmin.html")


# просмотр профиля пользователя
@app.route('/showuserseeadmin/<int:id_us>')
def showUserSeeAdmin(id_us):
    if 'loggedinadmin' in session:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute(
            "SELECT id_user, name, login, e_mail, telephone FROM userr WHERE id_user = %s;",
            (id_us,))
        show_user = cursor.fetchall()
        return render_template("showuserseeadmin.html", show_user=show_user)
    return render_template("loginadmin.html")


# удаление пользователя
@app.route('/deleteuser/<int:id_deleteuser>', methods=['GET', 'POST'])
def deleteUser(id_deleteuser):
    if request.method == 'POST':
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        if (request.form.get('yes', None)):

            # удаление публикаций пользователя
            cursor.execute(
                "DELETE FROM product WHERE id_user = %s",
                [id_deleteuser])
            conn.commit()

            # удаление пользователя
            cursor.execute(
                "DELETE FROM userr WHERE id_user = %s",
                [id_deleteuser])
            conn.commit()
            return redirect(url_for('adminSeeUser'))
    return render_template('deleteuser.html')
# конец функционала для администратора-модератора


#----------------------------Тестовая чать для добавления фотографий к объявлениям---------------
@app.route('/image')
def home():
    return render_template('example.html')


@app.route('/image', methods=['POST'])
def upload_image():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No image selected for uploading')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        # print('upload_image filename: ' + filename)

        cursor.execute("INSERT INTO upload (title) VALUES (%s)", (filename,))
        conn.commit()

        flash('Image successfully uploaded and displayed below')
        return render_template('example.html', filename=filename)
    else:
        flash('Allowed image types are - png, jpg, jpeg, gif')
        return redirect(request.url)


@app.route('/display/<filename>')
def display_image(filename):
    # print('display_image filename: ' + filename)
    return redirect(url_for('static', filename='image/' + filename), code=301)
#----------------------------------------------------------------------------------------------


@app.route('/about')
def about():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT * FROM userr;")
    list_users = cursor.fetchall()
    return render_template('about.html', list_users=list_users)


if __name__ == "__main__":
    app.run(debug=True)

