from collections import namedtuple
from flask import Flask, render_template, session, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from flask_wtf import Form
from wtforms import (StringField, SubmitField, IntegerField, BooleanField,
SelectField, FloatField, DateTimeField, validators, ValidationError, RadioField,
PasswordField)
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
    password = PasswordField('Password', validators=[Required()])
    submit = SubmitField('Log in')

@app.route('/', methods=['GET', 'POST'])
def index():
    form = LoginForm()
    if form.validate_on_submit():
        cursor = db.cursor()
        print("form.email.data=" + form.email.data)
        cursor.execute("select email, first_name, last_name " +
                       "from user where email = %s and password = %s",
                       (form.email.data, form.password.data))
        rows = cursor.fetchall()
        if rows:
            print("successful login")
            session['email'] = rows[0][0]
            session['customer_name'] = "{} {}".format(rows[0][1], rows[0][2])
            return redirect(url_for('home'))
        else:
            flash('Please enter a correct email/password combination.')
            return redirect(url_for('index'))
    return render_template('index.html', form=form)

@app.route('/logout')
def logout():
    session.pop('email', None)
    session.pop('customer_name', None)
    flash('You were logged out')
    return redirect(url_for('index'))

@app.route('/home')
def home():
    cursor = db.cursor()
    cursor.execute(
        "select distinct city as City, start_date, trip_id from trip " +
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
        db.commit()
        flash("Click on View Details to add activities to your new trip.")
        return redirect(url_for('home'))
    elif request.method=="GET":
        cursor.close()
        return render_template('createtrip.html', form=form)

@app.route('/trip/<tripid>')
# @app.route('/trip')
def trip(tripid):
    cursor = db.cursor()
    cursor.execute(
        "select attraction.name as Attraction, activity_date as Date, " +
        "start_time as Start, stop_time as Ends, price as Price, " +
        "nearest_pub_transit " +
        "from trip join activity using (trip_id) " +
        "join attraction using (attraction_id) where trip_id = %s",
        (tripid))
    trips = cursor.fetchall()
    cursor.execute("select city from trip where trip_id = %s", (tripid))
    city = cursor.fetchone()[0]
    cursor.execute("select purchase_completed from trip where trip_id = %s",
        (tripid))
    if cursor.fetchone()[0] == 1:
        not_paid = None
    else:
        not_paid = True
    cursor.close()
    return render_template('trip.html', trips = trips,
    unpaid = not_paid, tid = tripid, city = city)

class deleteActivityForm(Form):
    activities = SelectField('Activity', choices=[],
        validators=[Required("Select an activity to delete.")])
    submit = SubmitField('Delete Activity')


@app.route('/deleteactivity/<tripid>',  methods=['GET', 'POST'])
def deleteactivity(tripid):
    cursor = db.cursor()
    form = deleteActivityForm()
    cursor.execute("select activity_id, name from activity join attraction " +
        "using (attraction_id) where trip_id = %s" % (tripid))
    form.activities.choices = [(tup[0], tup[1]) for tup in cursor.fetchall()]
    if request.method=="POST":
        cursor.execute("delete from activity where activity_id=%s",
            (form.activities.data))
        cursor.close()
        db.commit()
        flash('Activity deleted from trip.')
        return redirect(url_for('trip', tripid = tripid))
    elif request.method=="GET":
        cursor.close()
        return render_template('deleteactivity.html', form=form, tripid = tripid)

class payForm(Form):
	isokay = BooleanField('Is this amount okay?',validators=[Required("You must check the box to continue.")])
	submit = SubmitField('Pay Now')

@app.route('/pay/<tripid>',methods=['GET', 'POST'])
def pay(tripid):
    cursor = db.cursor()
    sql1=("select sum(attraction.price) as Total from attraction join activity using(attraction_id) where activity.trip_id=%s" % (tripid))
    cursor.execute(sql1)
    amount = cursor.fetchall()
    column_names = [desc[0] for desc in cursor.description]
    cursor.close()
    form=payForm()
    if request.method=="POST":
        if form.validate()==False:
            flash('You must check the box before you continue.')
            return render_template('pay.html', form=form, tripid=tripid, rows=amount, columns=column_names)
        else:
            isokay=form.isokay.data
            cursor=db.cursor()
            sql1=("update trip set purchase_completed= 1 where trip_id=%s" %(tripid))
            cursor.execute(sql1)
            cursor.close()
            db.commit()
            return redirect(url_for("home"))
    elif request.method=="GET":
        return render_template('pay.html', form=form, tripid=tripid, rows=amount, columns=column_names)
    return render_template('pay.html', form=form, tripid=tripid, rows=amount, columns=column_names)

@app.route('/userprofile/<user>')
@app.route('/userprofile')
def userprofile(user = None):
    user = session['email'].split('@')[0]
    cursor = db.cursor()
    cursor.execute(
        "select user.last_name, user.first_name, user.email, user_address.street_no, user_address.street,"+
        " user_address.city, user_address.state, user_address.zip, user_address.country,"+
        " credit_card.credit_card_number from user join user_address using (email) join credit_card using (email) where user.email = %s",(session['email']))
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
        "select email, last_name, first_name from user order by email asc")
    rows=cursor.fetchall()
    column_names=[desc[0] for desc in cursor.description]
    cursor.close()
    return render_template('ADMINONLYusercontrolpage.html',
                           columns=column_names, rows=rows)

@app.route('/userinfo/<row>')
def userinfo(row):
	row=ast.literal_eval(row)
	uid=row[0]
	cursor=db.cursor()
	sql2= ("select * from user join user_address using(email) where email='%s'" % (uid))
	cursor.execute(sql2)
	userinfo=cursor.fetchall()
	column_names=[desc[0] for desc in cursor.description]
	cursor.close()
	return render_template('userinfo.html', columns=column_names, rows=userinfo, uid=uid)

class edituserForm(Form):
    street_no = StringField('Street Number')
    street = StringField('Street')
    city = StringField('City', validators=[Required()])
    state = StringField('State')
    zipcode = StringField('Zip Code', validators=[Required()])
    country = StringField('Country', validators=[Required()])
    ishold = BooleanField('Is this user on hold?')
    isadmin = BooleanField('Is this user an admin?')
    submit = SubmitField('Submit')

@app.route('/edituser/<uid>',methods=['GET', 'POST'])
def edituser(uid):
    form=edituserForm()
    if request.method=="POST":
        if form.validate()==False:
            return render_template('edituser.html',form=form, uid=uid)
        else:
            street_no=form.street_no.data
            if street_no:
                pass
            else:
                street_no="NULL"
            street=form.street.data
            if street:
                pass
            else:
                street="NULL"
            city=form.city.data
            state=form.state.data
            if state:
                pass
            else:
                state="NULL"
            zipcode=form.zipcode.data
            country=form.country.data
            ishold=form.ishold.data
            isadmin=form.isadmin.data
            cursor=db.cursor()
            sql1=("update user_address set street_no= %s, street='%s', city='%s',state='%s',zip='%s',country='%s' where email='%s'" %(street_no,street,city,state,zipcode,country,uid))
            sql2=("update user set on_hold=%s, is_admin=%s where email = '%s'" %(ishold, isadmin, uid))
            cursor.execute(sql1)
            cursor.execute(sql2)
            cursor.close()
            db.commit()
            return redirect(url_for('usercontrols'))
    elif request.method=="GET":
        return render_template('edituser.html', form=form, uid=uid)
    return render_template ('edituser.html', form=form, uid=uid)

@app.route('/deleteuser/<uid>')
def deleteuser(uid):
	cursor=db.cursor()
	sql1=("delete from user where email=%s" % (uid))
	cursor.execute(sql1)
	cursor.close()
	return redirect(url_for("usercontrols"))

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
	sql4= ("select * from attraction_hours where attraction_id=%i" % (aid))
	cursor.execute(sql4)
	attractionhours=cursor.fetchall()
	columns2=[desc[0] for desc in cursor.description]
	cursor.close()
	return render_template('attractioneditpage.html', columns=column_names, rows=attractioninfo, aid=aid, rows2=attractionhours,columns2=columns2)

@app.route('/deleteattraction/<aid>')
def deleteattraction(aid):
	cursor=db.cursor()
	sql1=("delete from attraction where attraction_id=%s" % (aid))
	cursor.execute(sql1)
	cursor.close()
	return redirect(url_for("attractioncontrols"))

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
    email=StringField('Email', validators=[Required()])
    first_name = StringField('First Name', validators=[Required()])
    last_name = StringField('Last Name', validators=[Required()])
    password = StringField('Password', validators=[Required()])
    street_no = StringField('Street Number', validators=[Required()])
    street = StringField('Street Name', validators=[Required()])
    city = StringField('City', validators=[Required()])
    state = StringField('State')
    zip_co = StringField('Zip', validators=[Required()])
    country = StringField('Country', validators=[Required()])
    credit_card_number=StringField('Credit Card Number',validators=[Required()])
    cvv=StringField('CVV',validators=[Required()])
    exp_yr=StringField('Expiration Year',validators=[Required()])
    exp_mo=StringField('Expiration Month',validators=[Required()])
    name_on_card=StringField('Name on Card',validators=[Required()])
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
    if request.method=="POST":
        if form.validate()==False:
            return render_template('registration.html', form=form)
        else:
            email=form.email.data
            first_name=form.first_name.data
            last_name=form.last_name.data
            password=form.password.data
            on_hold=0
            is_admin=0
            street_no=form.street_no.data
            street=form.street.data
            city=form.city.data
            state=form.state.data
            zip_co=form.zip_co.data
            country=form.country.data
            credit_card_number=form.credit_card_number.data
            cvv=form.cvv.data
            exp_yr=form.exp_yr.data
            exp_mo=form.exp_mo.data
            name_on_card=form.name_on_card.data
            cursor = db.cursor()
            sql1=("insert into user (email, first_name, last_name, password, on_hold, is_admin)" +
                "values('%s','%s','%s','%s',%s,%s)" % (email, first_name, last_name, password, on_hold, is_admin))
            sql2=("insert into user_address (street_no, street, city, state, zip, country)" +
                "values(%s,'%s','%s','%s',%s,'%s')" % (street_no, street, city, state, zip_co, country))
            sql3=("insert into credit_card (credit_card_number,cvv,exp_yr,exp_mo,name_on_card, email)" +
                "values(%s,%s,%s,%s,'%s','%s')" % (credit_card_number,cvv,exp_yr,exp_mo,name_on_card, email))
            cursor.execute(sql1)
            cursor.execute(sql2)
            cursor.execute(sql3)
            db.commit()
            cursor.execute("select email, first_name, last_name " +
                       "from user where email = %s",
                       (form.email.data,))
            rows = cursor.fetchall()
            cursor.close()
            session['email'] = rows[0][0]
            session['customer_name'] = "{} {}".format(rows[0][1], rows[0][2])
            return redirect(url_for('home'))
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

class attractionSearchForm(Form):
    city = StringField('City', [validators.AnyOf(message = "Not a valid city", values = ["Metz",
        "Paris", "Amsterdam"])])
    submit = SubmitField('Search')

@app.route('/attractionsearch', methods=['GET', 'POST'])
def attrsearch():
    city = None
    cursor = db.cursor()
    cursor.execute("select distinct city from attraction")
    form = attractionSearchForm()

    if request.method == "POST" and form.validate_on_submit():
        city = form.city.data
        #cursor.execute("select name, street_no, street, city, state, zip, description, " +
            #"nearest_pub_transit, price, reservation_required from attraction where city = %s ", (city))
        cursor.execute("select name, street_no, street, city, country, zip, price, reservation_required, description from attraction where city = %s", (city))
        attractions1=cursor.fetchall()
        column_names=[desc[0] for desc in cursor.description]
        cursor.close()
        attractions = []

        for a in attractions1:
            address = ""
            for x in range(1,6):
                if (a[x] != None) and (a[x] != "NULL") :
                    address += str(a[x]) + " "
            #address = str(a[1]) + " " + a[2] + ", " + a[3] + ", " + a[4] + " " + a[5]
            #return address
            if float(a[6]) == 0:
                price = "Free"
            else:
                price = a[6]
            if float(a[7]) == 0:
                res_req = "No"
            else:
                res_req = "Yes"
            a1 = (a[0], address, price, res_req, a[8])
            #return a1
            attractions.append(a1)
            #return address
        #return str(attractions[0][1])
        return render_template('attractionresults.html', city=city, attractions=attractions,
            columns=column_names)
    else:
        cursor.close()
        return render_template('attractionsearch.html', form = form)

@app.route('/attractionresults')
def attractionresults(city):
    return render_template('attractionresults.html', form=form)

class addActivityForm(Form):
    slots = SelectField('Available Time Slots', choices = [])
    addToTrip = SelectField("Select a trip to add to", choices = [])
    start = StringField("Activity Start Time (HH:MM)")
    end = StringField("Activity End Time (HH:MM)")
    numVisiting = StringField("Quantity")
    submit = SubmitField('Add Activity')

@app.route('/attractiondetails/<name>', methods=['GET', 'POST'])
def attractiondetails(name):
    cursor = db.cursor()
    form = addActivityForm()
    required = None
    cursor.execute("select street_no, street, city, zip, country, description, nearest_pub_transit, " +
        "price, reservation_required from attraction where name = %s", (name))
    entry = cursor.fetchone()
    address = ""
    for x in range(0,5):
        if (entry[x] != None) and (entry[x] != "NULL") :
            address += str(entry[x]) + " "
    attrCity = entry[2]
    des = entry[5]
    npt = entry[6]
    price = entry[7]
    if entry[8] == 1:
        required = "Yes"
    cursor.execute("select attraction_id from attraction where name = %s", (name))
    a_id = cursor.fetchone()[0]
    user = session['email']
    cursor.execute("select start_date from trip where email = %s", (user))
    tripTemp = [(tup[0], tup[0]) for tup in cursor.fetchall()]
    tripChoices = [(" ", " ")] + tripTemp
    form.addToTrip.choices = tripChoices
    cursor.execute("select start_time, stop_time, slot_quantity from attraction join time_slot " +
             "using (attraction_id) where attraction.name = %s", (name))
    aList = [(tup[0], tup[0]) for tup in cursor.fetchall()]
    choices = [(" ", " ")] + aList
    if len(aList) == 0:
        del form.slots
        if request.method == "POST":
            date1 = form.addToTrip.data.split(" ")
            actDate = date1[0]
            cursor.execute("select trip_id from trip where email = %s and start_date = %s", 
                (user, form.addToTrip.data))
            t_id = cursor.fetchone()[0]
            cursor.execute('select city from trip where trip_id = %s', (t_id))
            tripCity = cursor.fetchone()[0]
            if tripCity == attrCity:
                cursor.execute("insert into activity (start_time, stop_time, activity_date, attraction_id, trip_id) " +
                    "values (%s, %s, %s, %s, %s)", (form.start.data, form.end.data, actDate, a_id, t_id))
                cursor.close()
                flash("Activity Made")
                return redirect(url_for('home'))
            else:
                flash("Cannot add activity for an attraction not in " + tripCity)
                return render_template('attractiondetails.html', form=form, address=address, npt=npt,
                    required=required, price=price, name=name)
        else:
            cursor.close()
            return render_template('attractiondetails.html', form=form, address=address, npt=npt,
                required=required, price=price, name=name)
    else:
        form.slots.choices = choices
        del form.start
        del form.end
        if request.method == "POST":
            slot = form.slots.data.split(" ");
            date = slot[0].split("-")
            year = date[0]
            month = date[1]
            day = date[2]
            time = slot[1].split(":")
            hour = time[0]
            minute = time[1]
            cursor.execute("select slot_quantity, start_time, stop_time from time_slot join attraction using (attraction_id) where name = %s and year(start_time) = %s " + 
                "and month(start_time) = %s and day(start_time) = %s and hour(start_time) = %s" +
                " and minute(start_time) = %s", (name, year, month, day, hour, minute))
            q = cursor.fetchone()
            if int(form.numVisiting.data) < q[0]:
                cursor.execute("insert into reservations (attraction_id, slots_booked, start_time, " +
                    "stop_time) values (%s, %s, %s, %s)", (a_id, q[0], q[1], q[2]))
                newSlotQuantity = q[0] - int(form.numVisiting.data)
                cursor.execute("update time_slot set slot_quantity = %s where attraction_id = %s " +
                    "and start_time = %s", (newSlotQuantity, a_id, q[1]))
                cursor.close()
                flash("Reservation and Activity Made")
                return redirect(url_for('home'))
            else:
                cursor.close()
                flash("Not enough available slots for your request")
                return render_template('attractiondetails.html', form=form, name=name, address=address, 
                    required=required, npt=npt, price=price)
        else:
            cursor.close()
            return render_template('attractiondetails.html', form=form, name=name, address=address, 
                required=required, npt=npt, price=price)



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
