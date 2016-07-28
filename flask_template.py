from collections import namedtuple
from flask import Flask, render_template, session, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from flask_wtf import Form
from wtforms import (StringField, SubmitField, IntegerField, BooleanField,
SelectField, DateTimeField, validators, ValidationError, RadioField)
from wtforms.validators import Required
import pymysql
import getpass

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Taste the Rainbow'
bootstrap = Bootstrap(app)

def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash(u"Error in the %s field - %s" % (
                getattr(form, field).label.text,
                error
            ))

class LoginForm(Form):
    email = StringField('Email address', validators=[Required()])
    password = StringField('Password', validators=[Required()])
    submit = SubmitField('Log in')

@app.route('/', methods=['GET', 'POST'])
def index():
    form = LoginForm()
    if form.validate_on_submit():
        cursor = db.cursor()
        print("form.email.data=" + form.email.data)
        cursor.execute("select email, first_name, last_name " +
                       "from user where email = %s",
                       (form.email.data,))
        rows = cursor.fetchall()
        if rows:
            print("successful login")
            session['email'] = rows[0][0]
            session['customer_name'] = "{} {}".format(rows[0][1], rows[0][2])
            return redirect(url_for('home'))
        else:
            flash('Email address not found in user database.')
            return redirect(url_for('index'))
    return render_template('index.html', form=form)

@app.route('/home')
def home():
    cursor = db.cursor()
    cursor.execute(
        "select distinct city as City, start_date as Date from trip " +
        "join activity using (trip_id) " +
        "where start_date >= CURDATE() and email = %s",
        (session['email']))
    Trip = namedtuple('Trip', ['city', 'date'])
    trips = [Trip._make(row) for row in cursor.fetchall()]
    cursor.execute("select is_admin from user where email = %s",
        (session['email']))
    if cursor.fetchone()[0] == 1:
        admin = '1'
    else:
        admin = None
    try:
        cursor.execute(
            "select trip_id from trip " +
            "join activity using (trip_id) " +
            "where start_date >= CURDATE() and email = %s limit 1",
            (session['email']))
        trip = cursor.fetchone()[0]
    except:
        trip = None
    cursor.close()
    return render_template('home.html', trips=trips,
                           user=session['customer_name'], admuser = admin,
                           tid = trip)
class createtripForm(Form):
    city = SelectField('City', coerce = int, choices=[], validators=[Required("Select a city.")])
    start = DateTimeField('Start Date (YYYY-MM-DD HH:MM:SS)',
        format='%Y-%m-%d %H:%M:%S', validators=[Required("Please enter a date " +
        "and time in the format specified.")])
    end = DateTimeField('End Date (YYYY-MM-DD HH:MM:SS)',
        format='%Y-%m-%d %H:%M:%S', validators=[Required("Please enter a date " +
        "and time in the format specified.")])
    submit = SubmitField('Create Trip')


@app.route('/createtrip', methods=['GET', 'POST'])
def createtrip():
    cursor = db.cursor()
    cursor.execute("select distinct city from attraction")
    form = createtripForm(request.form)
    form.city.choices = [(i, tup[0]) for i,tup in enumerate(cursor.fetchall())]
    #SQL and verification whyyyyyyyy
    cursor.close()
    if request.method=="POST":
        print(form.validate())
        if form.validate() == False:
            print(type(form.city))
            print(type(form.start))
            print(type(form.end))
            flash('Please enter all information correctly.')
            return render_template('createtrip.html', form=form)
        else:
            return 'Form posted.'
    elif request.method=="GET":
        return render_template('createtrip.html', form=form)

@app.route('/trip/<tripid>')
# @app.route('/trip')
def trip(tripid):
    cursor = db.cursor()
    cursor.execute(
        "select attraction.name as Attraction, activity_date as Date, " +
        "start_time as Start, stop_time as Ends, price as Price " +
        "from trip join activity using (trip_id) " +
        "join attraction using (attraction_id) where trip_id = %s",
        (tripid))
    trips = cursor.fetchall()
    cursor.execute("select attraction.city from trip join activity using (trip_id) " +
        "join attraction using (attraction_id) where trip_id = %s limit 1", ('1'))
    trip_city = cursor.fetchone()[0]
    cursor.execute("select purchase_completed from trip where trip_id = %s",
        (tripid))
    if cursor.fetchone()[0] == 1:
        trip_paid = True
    else:
        trip_paid = False
    cursor.close()
    return render_template('trip.html', trips = trips, city = trip_city,
    paid = trip_paid)

@app.route('/edittrip')
def edittrip():
    return render_template('editttrip.html')

@app.route('/pay')
def pay():
    return render_template('pay.html')

@app.route('/userprofile/<user>')
@app.route('/userprofile')
def userprofile(user = None):
    user = session['email'].split('@')[0]
    cursor = db.cursor()
    cursor.execute(
        "select user.last_name, user.first_name, user.email, user_address.street_no, user_address.street, user_address.city, user_address.state, user_address.zip, user_address.country, credit_card.credit_card_number from user join user_address using(email) join credit_card using (address_id)")
    user = cursor.fetchall()
    delete = SubmitField("Delete Credit Card")
    edit = SubmitField("Edit Profile")
    column_names = [desc[0] for desc in cursor.description]
    cursor.close()
    return render_template('userprofile.html', columns=column_names, name = user)


@app.route('/usercontrols')
def usercontrols():
    cursor = db.cursor()
    cursor.execute(
        "select last_name, first_name, email from user order by last_name asc")
    rows=cursor.fetchall()
    edit= SubmitField("Edit")
    delete= SubmitField("Delete")
    column_names=[desc[0] for desc in cursor.description]
    cursor.close()
    return render_template('ADMINONLYusercontrolpage.html',
                           columns=column_names, rows=rows)

@app.route('/attractioncontrols')
def attractioncontrols():
    cursor = db.cursor()
    cursor.execute(
        "select attraction_id, name, city, country from attraction order by attraction_id asc")
    attractions=cursor.fetchall()
    column_names=[desc[0] for desc in cursor.description]
    cursor.close()
    return render_template('ADMINONLYattractioncontrolpage.html',
                           columns=column_names, rows=attractions)


@app.route('/attractionsearch')
def attrsearch():
    return render_template('attractionsearch.html')

class editccForm(Form):
    name_on_card = StringField('Name', validators=[Required()])
    credit_card_number = StringField('Credit Card Number', validators=[Required('Please enter your credit card number.')])
    CVV = StringField('CVV', validators=[Required('Please enter your CVV.')])
    expiration_year = StringField('Expiration Year (YYYY)', validators=[Required('Please enter your credit card expiration year.')])
    expiration_month = StringField('Expiration Month (MM)', validators=[Required('Please enter your credit card expiration month.')])
    address = RadioField('Billing Address', choices=[('1','Use shipping address'),('2', 'Enter a new billing address')], validators=[Required('Please select an option for billing address.')])
    submit = SubmitField('Submit')

@app.route('/editcc')
def editcc():
    form = editccForm()
    #verification and struggle bus sql things
    if request.method=="POST":
        return "Form posted"
    elif request.method=="GET":
        return render_template('editcc.html', form=form)

class addattractionForm(Form):
    name = StringField('Name', validators=[Required("Please enter the name of the attraction")])
    street_no = IntegerField('Street Number')
    street = StringField('Street')
    city = StringField('City', validators=[Required("Please enter the city")])
    state = StringField('State')
    zipcode = IntegerField('Zip Code', validators=[Required("Please enter the zip code")])
    country = StringField('Country', validators=[Required("Please enter the country")])
    description = StringField('Description', validators=[Required("Please enter a description")])
    nearestpubtransit = StringField('Nearest Public Transit', validators=[Required("Please enter the nearest public transit")])
    price=IntegerField("Price")
    resreq = BooleanField('Reservation Required')
    # MonOpen = SelectField('Opening time on Monday', choices=[(1,'Not open on Monday'),(2,'08:00:00'),(3,'08:30:00'),(4,'09:00:00'),(5,'09:30:00'),(6,'10:00:00'),(7,'10:30:00'),(8,'11:00:00'),(9,'11:30:00'),(10,'12:00:00'),(11,'12:30:00'),(12,'13:00:00'),(13,'13:30:00'),(14,'14:00:00'),(15,'14:30:00'),(16,'15:00:00'),(17,'15:30:00'),(18,'16:00:00')])
    # MonClosed = SelectField('Closing time on Monday', choices=[(1,'Not open on Monday'),(2,'15:00:00'),(3,'15:30:00'),(4,'16:00:00'),(5,'16:30:00'),(6,'17:00:00'),(7,'17:30:00'),(8,'18:00:00'),(9,'18:30:00'),(10,'19:00:00'),(11,'19:30:00'),(12,'20:00:00'),(13,'20:30:00'),(14,'21:00:00'),(15,'21:30:00'),(16,'22:00:00'),(17,'22:30:00'),(18,'23:00:00'),(19,'23:30:00'),(20,'23:59:59')])
    # TuesOpen = SelectField('Opening time on Tuesday', choices=[(1,'Not open on Tuesday'),(2,'08:00:00'),(3,'08:30:00'),(4,'09:00:00'),(5,'09:30:00'),(6,'10:00:00'),(7,'10:30:00'),(8,'11:00:00'),(9,'11:30:00'),(10,'12:00:00'),(11,'12:30:00'),(12,'13:00:00'),(13,'13:30:00'),(14,'14:00:00'),(15,'14:30:00'),(16,'15:00:00'),(17,'15:30:00'),(18,'16:00:00')])
    # TuesClosed = SelectField('Closing time on Tuesday', choices=[(1,'Not open on Tuesday'),(2,'15:00:00'),(3,'15:30:00'),(4,'16:00:00'),(5,'16:30:00'),(6,'17:00:00'),(7,'17:30:00'),(8,'18:00:00'),(9,'18:30:00'),(10,'19:00:00'),(11,'19:30:00'),(12,'20:00:00'),(13,'20:30:00'),(14,'21:00:00'),(15,'21:30:00'),(16,'22:00:00'),(17,'22:30:00'),(18,'23:00:00'),(19,'23:30:00'),(20,'23:59:59')])
    # WedOpen = SelectField('Opening time on Wednesday', choices=[(1,'Not open on Wednesday'),(2,'08:00:00'),(3,'08:30:00'),(4,'09:00:00'),(5,'09:30:00'),(6,'10:00:00'),(7,'10:30:00'),(8,'11:00:00'),(9,'11:30:00'),(10,'12:00:00'),(11,'12:30:00'),(12,'13:00:00'),(13,'13:30:00'),(14,'14:00:00'),(15,'14:30:00'),(16,'15:00:00'),(17,'15:30:00'),(18,'16:00:00')])
    # WedClosed = SelectField('Closing time on Wednesday', choices=[(1,'Not open on Wednesday'),(2,'15:00:00'),(3,'15:30:00'),(4,'16:00:00'),(5,'16:30:00'),(6,'17:00:00'),(7,'17:30:00'),(8,'18:00:00'),(9,'18:30:00'),(10,'19:00:00'),(11,'19:30:00'),(12,'20:00:00'),(13,'20:30:00'),(14,'21:00:00'),(15,'21:30:00'),(16,'22:00:00'),(17,'22:30:00'),(18,'23:00:00'),(19,'23:30:00'),(20,'23:59:59')])
    # ThursOpen = SelectField('Opening time on Thursday', choices=[(1,'Not open on Thursday'),(2,'08:00:00'),(3,'08:30:00'),(4,'09:00:00'),(5,'09:30:00'),(6,'10:00:00'),(7,'10:30:00'),(8,'11:00:00'),(9,'11:30:00'),(10,'12:00:00'),(11,'12:30:00'),(12,'13:00:00'),(13,'13:30:00'),(14,'14:00:00'),(15,'14:30:00'),(16,'15:00:00'),(17,'15:30:00'),(18,'16:00:00')])
    # ThursClosed = SelectField('Closing time on Thursday', choices=[(1,'Not open on Thursday'),(2,'15:00:00'),(3,'15:30:00'),(4,'16:00:00'),(5,'16:30:00'),(6,'17:00:00'),(7,'17:30:00'),(8,'18:00:00'),(9,'18:30:00'),(10,'19:00:00'),(11,'19:30:00'),(12,'20:00:00'),(13,'20:30:00'),(14,'21:00:00'),(15,'21:30:00'),(16,'22:00:00'),(17,'22:30:00'),(18,'23:00:00'),(19,'23:30:00'),(20,'23:59:59')])
    # FriOpen = SelectField('Opening time on Friday', choices=[(1,'Not open on Friday'),(2,'08:00:00'),(3,'08:30:00'),(4,'09:00:00'),(5,'09:30:00'),(6,'10:00:00'),(7,'10:30:00'),(8,'11:00:00'),(9,'11:30:00'),(10,'12:00:00'),(11,'12:30:00'),(12,'13:00:00'),(13,'13:30:00'),(14,'14:00:00'),(15,'14:30:00'),(16,'15:00:00'),(17,'15:30:00'),(18,'16:00:00')])
    # FriClosed = SelectField('Closing time on Friday', choices=[(1,'Not open on Friday'),(2,'15:00:00'),(3,'15:30:00'),(4,'16:00:00'),(5,'16:30:00'),(6,'17:00:00'),(7,'17:30:00'),(8,'18:00:00'),(9,'18:30:00'),(10,'19:00:00'),(11,'19:30:00'),(12,'20:00:00'),(13,'20:30:00'),(14,'21:00:00'),(15,'21:30:00'),(16,'22:00:00'),(17,'22:30:00'),(18,'23:00:00'),(19,'23:30:00'),(20,'23:59:59')])
    # SatOpen = SelectField('Opening time on Saturday', choices=[(1,'Not open on Saturday'),(2,'08:00:00'),(3,'08:30:00'),(4,'09:00:00'),(5,'09:30:00'),(6,'10:00:00'),(7,'10:30:00'),(8,'11:00:00'),(9,'11:30:00'),(10,'12:00:00'),(11,'12:30:00'),(12,'13:00:00'),(13,'13:30:00'),(14,'14:00:00'),(15,'14:30:00'),(16,'15:00:00'),(17,'15:30:00'),(18,'16:00:00')])
    # SatClosed = SelectField('Closing time on Saturday', choices=[(1,'Not open on Saturday'),(2,'15:00:00'),(3,'15:30:00'),(4,'16:00:00'),(5,'16:30:00'),(6,'17:00:00'),(7,'17:30:00'),(8,'18:00:00'),(9,'18:30:00'),(10,'19:00:00'),(11,'19:30:00'),(12,'20:00:00'),(13,'20:30:00'),(14,'21:00:00'),(15,'21:30:00'),(16,'22:00:00'),(17,'22:30:00'),(18,'23:00:00'),(19,'23:30:00'),(20,'23:59:59')])
    # SunOpen = SelectField('Opening time on Sunday', choices=[(1,'Not open on Sunday'),(2,'08:00:00'),(3,'08:30:00'),(4,'09:00:00'),(5,'09:30:00'),(6,'10:00:00'),(7,'10:30:00'),(8,'11:00:00'),(9,'11:30:00'),(10,'12:00:00'),(11,'12:30:00'),(12,'13:00:00'),(13,'13:30:00'),(14,'14:00:00'),(15,'14:30:00'),(16,'15:00:00'),(17,'15:30:00'),(18,'16:00:00')])
    # SunClosed = SelectField('Closing time on Sunday', choices=[(1,'Not open on Sunday'),(2,'15:00:00'),(3,'15:30:00'),(4,'16:00:00'),(5,'16:30:00'),(6,'17:00:00'),(7,'17:30:00'),(8,'18:00:00'),(9,'18:30:00'),(10,'19:00:00'),(11,'19:30:00'),(12,'20:00:00'),(13,'20:30:00'),(14,'21:00:00'),(15,'21:30:00'),(16,'22:00:00'),(17,'22:30:00'),(18,'23:00:00'),(19,'23:30:00'),(20,'23:59:59')])
    submit = SubmitField('Add Attraction')

class registrationForm(Form):
    name = StringField('Name', validators=[Required()])
    street_no = StringField('Street Number', validators=[Required()])
    street = StringField('Street', validators=[Required()])
    city = StringField('City', validators=[Required()])
    state = StringField('State', validators=[Required()])
    zipcode = StringField('Zip Code', validators=[Required()])
    country = StringField('Country', validators=[Required()])
    submit = SubmitField('Create Account')


@app.route('/addattraction', methods=['GET','POST'])
def addattraction():
    form = addattractionForm()
    #verification and struggle bus sql things
    #http://code.tutsplus.com/tutorials/intro-to-flask-adding-a-contact-page--net-28982
    if request.method=="POST":
        if form.validate()==False:
            return render_template('ADMINONLYaddattractionpage.html', form=form)
        else:
            name=str(form.name.data)
            street_no=form.street_no.data
            if street_no:
                pass
            else:
                street_no="NULL"
            street=str(form.street.data)
            if street:
                pass
            else:
                street="NULL"
            city=str(form.city.data)
            state=str(form.state.data)
            if state:
                pass
            else:
                state="NULL"
            zipcode=form.zipcode.data
            country=str(form.country.data)
            description=str(form.description.data)
            nearestpubtransit=str(form.nearestpubtransit.data)
            price=form.price.data
            resreq=form.resreq.data
            if resreq==True:
                resreq=1
            else:
                resreq=0
            cursor = db.cursor()
            sql1=("insert into attraction (name, street_no, street, city, state, zip, country, description, nearest_pub_transit, price, reservation_required)" + 
                "values('%s',%i,'%s','%s','%s',%i,'%s','%s','%s',%i,%i)" % (name, street_no, street, city, state, zipcode, country, description, nearestpubtransit, price, resreq))
            cursor.execute(sql1)
            cursor.close()
            db.commit()
            return sql1
    elif request.method=="GET":
        return render_template('ADMINONLYaddattractionpage.html', form=form)

@app.route('/registration', methods=['GET','POST'])
def registration():
    form = registrationForm()
    #SQL insert statements
    if request.method=="POST":
        return "Form posted"
    elif request.method=="GET":
        return render_template('registration.html', form=form)

@app.route('/editprof/<user>')
@app.route('/editprof', methods=['GET','POST'])
def editprof():
    user = session['email'].split('@')[0]
    cursor = db.cursor()
    cursor.execute("select first_name, last_name, email from user where email = %s",
        (session['email']))
    user = cursor.fetchall()
    column_names = [desc[0] for desc in cursor.description]
    cursor.close()
    form = editprofForm()
    #verification and struggle bus sql things
    if request.method=="POST":
        return "Form posted"
    elif request.method=="GET":
        return render_template('editprof.html', form=form, columns=column_names, name=user)

class editprofForm(Form):
    password = StringField('Change Password', validators=[Required()])
    street_no = StringField('Street Number', validators=[Required()])
    street = StringField('Street', validators=[Required()])
    city = StringField('City', validators=[Required()])
    state = StringField('State', validators=[Required()])
    zipcode = StringField('Zip Code', validators=[Required()])
    country = StringField('Country', validators=[Required()])
    submit = SubmitField('Submit')

@app.route('/browse_db')
def browse_db():
    cursor = db.cursor()
    cursor.execute("show tables")
    tables = [field[0] for field in cursor.fetchall()]
    cursor.close()
    return render_template('browse_db.html', dbname=dbname, tables=tables)

@app.route('/table/<table>')
def table(table):
    cursor = db.cursor()
    cursor.execute("select * from " + table)
    rows = cursor.fetchall()
    column_names = [desc[0] for desc in cursor.description]
    cursor.close()
    return render_template('table.html', table=table,
                           columns=column_names, rows=rows)

if __name__ == '__main__':
    dbname = 'team3'
    db = pymysql.connect(host='localhost',user='root', passwd='',db=dbname)
    cursor = db.cursor()
    app.run(debug=True)
    db.close()
