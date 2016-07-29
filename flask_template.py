from collections import namedtuple
from flask import Flask, render_template, session, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from flask_wtf import Form
from wtforms import (StringField, SubmitField, IntegerField, BooleanField,
SelectField, FloatField, DateTimeField, validators, ValidationError, RadioField)
from wtforms.validators import Required
import pymysql
import getpass
import ast

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
        "select distinct city as City, start_date as Date, trip_id from trip " +
        # "join activity using (trip_id) " +
        "where start_date >= CURDATE() and email = %s",
        (session['email']))
    Trip = namedtuple('Trip', ['city', 'date', 'trip_id'])
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
            # "join activity using (trip_id) " +
            "where start_date >= CURDATE() and email = %s order by trip_id",
            (session['email']))
        trip_ids = cursor.fetchone()[0]
    except:
        trip_ids = None
    cursor.close()
    return render_template('home.html', trips=trips,
                           user=session['customer_name'], admuser = admin)
class createtripForm(Form):
    city = SelectField('City', choices=[],
        validators=[Required("Select a city.")])
    start = StringField('Start Date (YYYY-MM-DD)',
         validators=[Required("Please enter a date " +
        "and time in the format specified.")])
    end = StringField('End Date (YYYY-MM-DD)',
        validators=[Required("Please enter a date " +
        "and time in the format specified.")])
    submit = SubmitField('Create Trip')


@app.route('/createtrip', methods=['GET', 'POST'])
def createtrip():
    cursor = db.cursor()
    cursor.execute("select distinct city from attraction")
    form = createtripForm()
    form.city.choices = [(tup[0], tup[0]) for tup in cursor.fetchall()]
    #SQL and verification whyyyyyyyy
    if request.method=="POST":
        # if form.validate() == False:
        #     flash('Please enter all information correctly.')
        #     return render_template('createtrip.html', form=form)
        # else:
        print(form.city.data)
        print(form.start.data)
        print(form.end.data)
        cursor.execute("insert into trip (email,start_date,end_date,city, total_cost, purchase_completed) " +
            "values (%s,%s,%s,%s, 0.0, 0)", (session['email'],form.start.data,
            form.end.data, form.city.data))
        cursor.close()
        return 'Form posted.'
    elif request.method=="GET":
        cursor.close()
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
    cursor.execute("select purchase_completed from trip where trip_id = %s",
        (tripid))
    if cursor.fetchone()[0] == 1:
        trip_paid = None
    else:
        trip_paid = True
    cursor.close()
    return render_template('trip.html', trips = trips,
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
        "select user.last_name, user.first_name, user.email, user_address.street_no, user_address.street,"+
        " user_address.city, user_address.state, user_address.zip, user_address.country,"+
        " credit_card.credit_card_number from user join user_address using(email) join credit_card using (email) where user.email = %s",(session['email']))
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

@app.route('/attractioninfopage/<row>')
def attractioninfopage(row):
	row=ast.literal_eval(row)
	aid=row[0]
	cursor = db.cursor()
	sql2= ("select * from attraction where attraction_id=%i" % (aid))
	cursor.execute(sql2)
	attractioninfo=cursor.fetchall()
	column_names=[desc[0] for desc in cursor.description]
	cursor.close()
	return render_template('attractioneditpage.html', columns=column_names, rows=attractioninfo, aid=aid)

@app.route('/editattraction/<aid>', methods=['GET','POST'])
def editattraction(aid):
    form = editattractionForm()
    if request.method=="POST":
        if form.validate()==False:
            return render_template('editattraction.html', form=form)
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
            sql1=("update attraction set name='%s', street_no= %i, street='%s', city='%s',state='%s',zip=%s,country='%s',description='%s',nearest_pub_transit='%s',price=%s,reservation_required=%s where attraction_id=%s" %(name,street_no,street,city,state,zipcode,country,description,nearestpubtransit,price,resreq,aid))
            cursor.execute(sql1)
            sql2=("select attraction_id, name, city, country from attraction where attraction_id=%s" % (aid))
            cursor.execute(sql2)
            row=cursor.fetchall()
            cursor.close()
            db.commit()
            return redirect(url_for("attractioncontrols"))
    elif request.method=="GET":
        return render_template('editattraction.html', form=form)

@app.route('/attractionsearch')
def attrsearch():
    return render_template('attractionsearch.html')

class editccForm(Form):
    name_on_card = StringField('Name', validators=[Required()])
    credit_card_number = StringField('Credit Card Number', validators=[Required('Please enter your credit card number.')])
    CVV = StringField('CVV', validators=[Required('Please enter your CVV.')])
    expiration_year = StringField('Expiration Year (YYYY)', validators=[Required('Please enter your credit card expiration year.')])
    expiration_month = StringField('Expiration Month (MM)', validators=[Required('Please enter your credit card expiration month.')])
    street_no = IntegerField('Street Number')
    street = StringField('Street')
    city = StringField('City', validators=[Required("Please enter the city")])
    state = StringField('State')
    zipcode = IntegerField('Zip Code', validators=[Required("Please enter the zip code")])
    country = StringField('Country', validators=[Required("Please enter the country")])
    submit = SubmitField('Submit')

@app.route('/editcc', methods=['GET','POST'])
def editcc():
    form = editccForm()
    if request.method=="POST":
        if form.validate() == False:
            return render_template('editcc.html', form=form)
        else:
            name=str(form.name_on_card.data)
            ccn=int(form.credit_card_number.data)
            cvv=int(form.CVV.data)
            exp_yr=int(form.expiration_year.data)
            exp_mo=int(form.expiration_month.data)
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
            cursor = db.cursor()
            sql1=("update user_address set street_no= %i, street='%s', city='%s',state='%s',zip='%s',country='%s' where email='%s'" %(street_no,street,city,state,zipcode,country,session['email']))
            sql2=("update credit_card set credit_card_number= %i,cvv=%i ,exp_yr= %i,exp_mo=%i,name_on_card='%s' where email ='%s'" %(ccn,cvv,exp_yr,exp_mo,name,session['email']))
            cursor.execute(sql1)
            cursor.execute(sql2)
            cursor.close()
            db.commit()
            return redirect(url_for('userprofile'))
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
    price = FloatField("Price")
    resreq = BooleanField('Reservation Required')
    MonOpen = StringField('Opening hour on Monday (in the form HH:MM:SS)')
    MonClose = StringField('Closing hour on Monday (in the form HH:MM:SS)')
    TuesOpen = StringField('Opening hour on Tuesday (in the form HH:MM:SS)')
    TuesClose = StringField('Closing hour on Tuesday (in the form HH:MM:SS)')
    WedOpen = StringField('Opening hour on Wednesday (in the form HH:MM:SS)')
    WedClose = StringField('Closing hour on Wednesday (in the form HH:MM:SS)')
    ThursOpen = StringField('Opening hour on Thursday (in the form HH:MM:SS)')
    ThursClose = StringField('Closing hour on Thursday (in the form HH:MM:SS)')
    FriOpen = StringField('Opening hour on Friday (in the form HH:MM:SS)')
    FriClose = StringField('Closing hour on Friday (in the form HH:MM:SS)')
    SatOpen = StringField('Opening hour on Saturday (in the form HH:MM:SS)')
    SatClose = StringField('Closing hour on Saturday (in the form HH:MM:SS)')
    SunOpen = StringField('Opening hour on Sunday (in the form HH:MM:SS)')
    SunClose = StringField('Closing hour on Sunday (in the form HH:MM:SS)')
    submit = SubmitField('Add Attraction')

class editattractionForm(Form):
    name = StringField('Name', validators=[Required("Please enter the name of the attraction")])
    street_no = IntegerField('Street Number')
    street = StringField('Street')
    city = StringField('City', validators=[Required("Please enter the city")])
    state = StringField('State')
    zipcode = IntegerField('Zip Code', validators=[Required("Please enter the zip code")])
    country = StringField('Country', validators=[Required("Please enter the country")])
    description = StringField('Description', validators=[Required("Please enter a description")])
    nearestpubtransit = StringField('Nearest Public Transit', validators=[Required("Please enter the nearest public transit")])
    price = FloatField("Price")
    resreq = BooleanField('Reservation Required')
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
            MonOpen=form.MonOpen.data
            MonClose=form.MonClose.data
            TuesOpen=form.TuesOpen.data
            TuesClose=form.TuesClose.data
            WedOpen=form.WedOpen.data
            WedClose=form.WedClose.data
            ThursOpen=form.ThursOpen.data
            ThursClose=form.ThursClose.data
            FriOpen=form.FriOpen.data
            FriClose=form.FriClose.data
            SatOpen=form.SatOpen.data
            SatClose=form.SatClose.data
            SunOpen=form.SunOpen.data
            SunClose=form.SunClose.data
            if resreq==True:
                resreq=1
            else:
                resreq=0
            if MonOpen:
                pass
            else:
                MonOpen="NULL"
            if MonClose:
                pass
            else:
                MonClose="NULL"
            if TuesOpen:
                pass
            else:
                TuesOpen="NULL"
            if TuesClose:
                pass
            else:
                TuesClose="NULL"
            if WedOpen:
                pass
            else:
                WedOpen="NULL"
            if WedClose:
                pass
            else:
                WedClose="NULL"
            if ThursOpen:
                pass
            else:
                ThursOpen="NULL"
            if ThursClose:
                pass
            else:
                ThursClose="NULL"
            if FriOpen:
                pass
            else:
                FriOpen="NULL"
            if FriClose:
                pass
            else:
                FriClose="NULL"
            if SatOpen:
                pass
            else:
                SatOpen="NULL"
            if SatClose:
                pass
            else:
                SatClose="NULL"
            if SunOpen:
                pass
            else:
                SunOpen="NULL"
            if SunClose:
                pass
            else:
                SunClose="NULL"
            cursor = db.cursor()
            sql1=("insert into attraction (name, street_no, street, city, state, zip, country, description, nearest_pub_transit, price, reservation_required)" +
                "values('%s',%i,'%s','%s','%s',%i,'%s','%s','%s',%i,%i)" % (name, street_no, street, city, state, zipcode, country, description, nearestpubtransit, price, resreq))
            sql2=("select attraction_id from attraction where name='%s'" % (name))
            cursor.execute(sql1)
            cursor.close()
            db.commit()
            cursor=db.cursor()
            cursor.execute(sql2)
            aid=cursor.fetchone()
            aid=str(aid)
            aid=aid[1:-2]
            aid=int(aid)
            if MonOpen != 'NULL':
            	sql3=("insert into attraction_hours (attraction_id, day_of_week,hour_open,hour_close)"+
            		"values(%s,'Monday','%s','%s')" % (aid,MonOpen,MonClose))
            	cursor.execute(sql3)
            if TuesOpen != 'NULL':
            	sql3=("insert into attraction_hours (attraction_id, day_of_week,hour_open,hour_close)"+
            		"values(%s,'Tuesday','%s','%s')" % (aid,TuesOpen,TuesClose))
            	cursor.execute(sql3)
            if WedOpen != 'NULL':
            	sql3=("insert into attraction_hours (attraction_id, day_of_week,hour_open,hour_close)"+
            		"values(%s,'Wednesday','%s','%s')" % (aid,WedOpen,WedClose))
            	cursor.execute(sql3)
            if ThursOpen != 'NULL':
            	sql3=("insert into attraction_hours (attraction_id, day_of_week,hour_open,hour_close)"+
            		"values(%s,'Thursday','%s','%s')" % (aid,ThursOpen,ThursClose))
            	cursor.execute(sql3)
            if FriOpen != 'NULL':
            	sql3=("insert into attraction_hours (attraction_id, day_of_week,hour_open,hour_close)"+
            		"values(%s,'Friday','%s','%s')" % (aid,FriOpen,FriClose))
            	cursor.execute(sql3)
            if SatOpen != 'NULL':
            	sql3=("insert into attraction_hours (attraction_id, day_of_week,hour_open,hour_close)"+
            		"values(%s,'Saturday','%s','%s')" % (aid,SatOpen,SatClose))
            	cursor.execute(sql3)
            if SunOpen != 'NULL':
            	sql3=("insert into attraction_hours (attraction_id, day_of_week,hour_open,hour_close)"+
            		"values(%s,'Sunday','%s','%s')" % (aid,SunOpen,SunClose))
            	cursor.execute(sql3)
            cursor.close()
            db.commit()
            return redirect(url_for('attractioncontrols'))
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
        if form.validate()==False:
            return render_template('editprof.html',form=form)
        else:
            password=str(form.password.data)
            street_no=int(form.street_no.data)
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
            zipcode=str(form.zipcode.data)
            country=str(form.country.data)
            cursor=db.cursor()
            sql1=("update user_address set street_no= %i, street='%s', city='%s',state='%s',zip='%s',country='%s' where email='%s'" %(street_no,street,city,state,zipcode,country,session['email']))
            sql2=("update user set password='%s' where email = '%s'" %(password, session['email']))
            cursor.execute(sql1)
            cursor.execute(sql2)
            cursor.close()
            db.commit()
            return redirect(url_for('userprofile'))
    elif request.method=="GET":
        return render_template('editprof.html', form=form, columns=column_names, name=user)

class editprofForm(Form):
    password = StringField('Change Password', validators=[Required()])
    street_no = StringField('Street Number')
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
