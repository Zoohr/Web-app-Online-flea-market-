def create_database():
    postgre_database = '''
    DROP TABLE IF EXISTS photo;
    DROP TABLE IF EXISTS product;
    DROP TABLE IF EXISTS category;
    DROP TABLE IF EXISTS estimation;
    DROP TABLE IF EXISTS userr;
    DROP TABLE IF EXISTS city;


    CREATE TABLE city(
            id_city INT PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
            city_name varchar(50) NOT NULL);

    CREATE TABLE userr(
            id_user INT PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
            name varchar(50) NOT NULL,
            login varchar(50) NOT NULL,
            e_mail varchar(50) NOT NULL,
            password varchar(256) NOT NULL,
            telephone varchar(50),
            id_city INT REFERENCES city(id_city));

    CREATE TABLE estimation(
            id_esti INT PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
			id_profile INT NOT NULL,
            mark integer NOT NULL,
			text varchar(500),
            date DATE,
            id_user INT REFERENCES userr(id_user));

    CREATE TABLE category(
            id_category INT PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
            category_name varchar(50) NOT NULL);

    CREATE TABLE product(
            id_product INT PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
            product_name varchar(100) NOT NULL,
            cost varchar(50) NOT NULL,
            description varchar(1000) NOT NULL,
            id_user INT REFERENCES userr(id_user),
            id_category INT REFERENCES category(id_category));

    CREATE TABLE photo(
            id_photo INT PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
            title VARCHAR (100) NOT NULL,
            id_product INT REFERENCES product(id_product));
            
    CREATE TABLE admin(
            id_admin INT PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
            login varchar(50) NOT NULL,
            password varchar(256) NOT NULL);           
    '''
    return postgre_database