from collections import namedtuple
from flask import Flask, render_template, session, redirect, url_for, flash
from flask_bootstrap import Bootstrap
from flask_wtf import Form
from wtforms import StringField, SubmitField
from wtforms.validators import Required
import pymysql

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hard to guess string'
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
        "select city as City, trip_date as Date from trip " +
        "where trip_date >= CURDATE() and email = %s",
        (session['email']))
    Trip = namedtuple('Trip', ['city', 'date'])
    trips = [Trip._make(row) for row in cursor.fetchall()]
    cursor.close()
    return render_template('home.html', trips=trips,
                           user=session['customer_name'])

@app.route('/createtrip')
def createtrip():
    return render_template('createtrip.html')

@app.route('/trip')
def trip():
    return render_template('trip.html')

@app.route('/userprofile/<user>')
def userprofile(user):
    user = session['email'].split('@')[0]
    return render_template('userprofile.html', name=session['customer_name'])

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
        "select name, city, country from attraction order by name asc")
    rows=cursor.fetchall()
    column_names=[desc[0] for desc in cursor.description]
    cursor.close()
    return render_template('ADMINONLYattractioncontrolpage.html',
                           columns=column_names, rows=rows)

@app.route('/addattraction',methods=['GET', 'POST'])
def addattraction():
    form=addattractionForm()
    #validate statements
    return render_template('ADMINONLYaddattractionpage.html', form=form)

class addattractionForm():
    name = StringField('Name', validators=[Required()])
    street_no = StringField('Street Number', validators=[Required()])
    street = StringField('Street', validators=[Required()])
    city = StringField('City', validators=[Required()])
    state = StringField('State', validators=[Required()])
    zipcode = StringField('Zip Code', validators=[Required()])
    country = StringField('Country', validators=[Required()])
    description = StringField('Description', validators=[Required()])
    nearestpubtransit = StringField('Nearest Public Transit', validators=[Required()])
    resreq = StringField('Reservation Required (Y/N)', validators=[Required()])
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

##def addattractionForm():
##    name = StringField('Name', validators=[Required()])
##    street_no = StringField('Street Number', validators=[Required()])
##    street = StringField('Street', validators=[Required()])
##    city = StringField('City', validators=[Required()])
##    state = StringField('State', validators=[Required()])
##    zipcode = StringField('Zip Code', validators=[Required()])
##    country = StringField('Country', validators=[Required()])
##    description = StringField('Description', validators=[Required()])
##    nearestpubtransit = StringField('Nearest Public Transit', validators=[Required()])
##    resreq = StringField('Reservation Required (Y/N)', validators=[Required()])
##    MonOpen = StringField('Opening hour on Monday', validators=[Required()])
##    MonClosed = StringField('Closing hour on Monday', validators=[Required()])
##    TuesOpen = StringField('Opening hour on Tuesday', validators=[Required()])
##    TuesClosed = StringField('Closing hour on Tuesday', validators=[Required()])
##    WedOpen = StringField('Opening hour on Wednesday', validators=[Required()])
##    WedClosed = StringField('Closing hour on Wednesday', validators=[Required()])
##    ThursOpen = StringField('Opening hour on Thursday', validators=[Required()])
##    ThursClosed = StringField('Closing hour on Thursday', validators=[Required()])
##    FriOpen = StringField('Opening hour on Friday', validators=[Required()])
##    FriClosed = StringField('Closing hour on Friday', validators=[Required()])
##    SatOpen = StringField('Opening hour on Saturday', validators=[Required()])
##    SatClosed = StringField('Closing hour on Saturday', validators=[Required()])
##    SunOpen = StringField('Opening hour on Sunday', validators=[Required()])
##    SunClosed = StringField('Closing hour on Sunday', validators=[Required()])
##    submit = SubmitField('Add Attraction')


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
