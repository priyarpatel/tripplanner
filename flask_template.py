from collections import namedtuple
from flask import Flask, render_template, session, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from flask_wtf import Form
from wtforms import StringField, SubmitField, BooleanField, validators
from wtforms.validators import Required
import pymysql

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Taste the Rainbow'
bootstrap = Bootstrap(app)

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

@app.route('/createtrip')
def createtrip():
    return render_template('createtrip.html')

@app.route('/trip/<tripid>')
@app.route('/trip')
def trip(tripid = None):
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
    cursor.close()
    return render_template('trip.html', trips = trips, city = trip_city)

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

@app.route('/deletecc')
def deletecc():
    return render_template('deletecc.html')

class addattractionForm(Form):
    name = StringField('Name', validators=[Required()])
    street_no = StringField('Street Number', validators=[Required()])
    street = StringField('Street', validators=[Required()])
    city = StringField('City', validators=[Required()])
    state = StringField('State', validators=[Required()])
    zipcode = StringField('Zip Code', validators=[Required()])
    country = StringField('Country', validators=[Required()])
    description = StringField('Description', validators=[Required()])
    nearestpubtransit = StringField('Nearest Public Transit', validators=[Required()])
    resreq = BooleanField('Reservation Required', validators=[Required()])
    MonOpen = StringField('Opening hour on Monday', validators=[Required()])
    MonClosed = StringField('Closing hour on Monday', validators=[Required()])
    TuesOpen = StringField('Opening hour on Tuesday', validators=[Required()])
    TuesClosed = StringField('Closing hour on Tuesday', validators=[Required()])
    WedOpen = StringField('Opening hour on Wednesday', validators=[Required()])
    WedClosed = StringField('Closing hour on Wednesday', validators=[Required()])
    ThursOpen = StringField('Opening hour on Thursday', validators=[Required()])
    ThursClosed = StringField('Closing hour on Thursday', validators=[Required()])
    FriOpen = StringField('Opening hour on Friday', validators=[Required()])
    FriClosed = StringField('Closing hour on Friday', validators=[Required()])
    SatOpen = StringField('Opening hour on Saturday', validators=[Required()])
    SatClosed = StringField('Closing hour on Saturday', validators=[Required()])
    SunOpen = StringField('Opening hour on Sunday', validators=[Required()])
    SunClosed = StringField('Closing hour on Sunday', validators=[Required()])
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
    if request.method=="POST":
        return "Form posted"
    elif request.method=="GET":
        return render_template('ADMINONLYaddattractionpage.html', form=form)

@app.route('/registration', methods=['GET','POST'])
def registration():
    form = addattractionForm()
    #SQL insert statements
    if request.method=="POST":
        return "Form posted"
    elif request.method=="GET":
        return render_template('registration.html', form=form)

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
    app.run(debug=True)
    db.close()
