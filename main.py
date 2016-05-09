import webapp2
from google.appengine.ext import ndb
import mimetypes
import logging
from google.appengine.api import images
from google.appengine.api import users
from google.appengine.api import mail
from google.appengine.api import app_identity
from google.appengine.api import search
import urllib



HTML_FORMS = \
    """
<form action="/img_upload" enctype="multipart/form-data" method="post">
    <fieldset>
        <legend>Post your own image:</legend>
        <div><input type="file" name="imgFile"></div>
        <dib><input type="text" name="caption" placeholder="add caption" style="width:600px;height:25px;"></div>
        <div><input type="text" name="hashText" placeholder= "Tags" style="width:300px;height:25px;">(max 3)</div>
        <div><input type="submit" value="Upload"></div>
    </fieldset>
</form>
<br>
<form action="/img_search" method="post">
    <fieldset>
        <legend>Search by hashtag</legend>
        <div><input type="text" name="textToSearch" placeholder= "Search by hashtag(only one)" style="width:300px;height:25px;"></div>
        <div><input type="submit" value="Search"></div>
    </fieldset>
</form>
<br>
<form action="/invite" method="post">
    <legend>Invite Friend</legend>
    <input type="email" name="friend_email" placeholder="Friend's e-mail">
    <input type="submit" value="Send Invite">
</form>

     """


class UserImage(ndb.Model):
    imgData = ndb.BlobProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)
    author = ndb.StringProperty()
    file_name=ndb.StringProperty()
    hash_Text = ndb.StringProperty()
    caption = ndb.StringProperty()

def image_key(image_name=None):
    """Constructs a Datastore key for a UserImage entity with name."""
    return ndb.Key('Mime', image_name or 'default_image')


# class MainPage(webapp2.RequestHandler):
#     def get(self):
#         user = users.get_current_user()
#     	if user:
# 	    	self.response.write( '<!DOCTYPE HTML><html lang="en">')
# 	    	self.response.write(HTML_Main_PAGE)
#         self.response.write('<a href="http://localhost:8080/img_portal">My_images')
#         self.response.write('<br>')
#         self.response.write('</html>')
#         self.response.write('<a href='+users.create_logout_url('/')+'>Logout')
#       else:
#         self.response.write('<a href='+users.create_login_url('/')+'>Login')



#Handler for image upload
class FileUpload(webapp2.RequestHandler):
    def post(self):
        #Creating entity with fixed id
        user = users.get_current_user()
        #imgObj = UserImage(id=user.nickname())
        imgObj = UserImage(id="mainEnti")
        imgObj = UserImage(parent=image_key("mainEnti"))


        #Below lines to be added in the main code to put image in datastore
        img_upload = self.request.POST.get("imgFile", None)
        imgObj.file_name = img_upload.filename
        imgObj.caption = self.request.POST.get("caption",None)
        avatar= img_upload.file.read()
        avatar= images.resize(avatar, 300,300)
        imgObj.imgData= avatar
        imgObj.author=user.nickname()
        imgObj.hash_Text = self.request.POST.get("hashText",None)
        listHashText = imgObj.hash_Text.split(" ")
        userKey = imgObj.put()
        FileUpload.createDocument(self,imgObj,userKey,listHashText)
        self.redirect('/')

    def createDocument(self,imgObj,key,listHashText):
        for i in listHashText:
            doc = search.Document(doc_id=str(key.urlsafe())+str(i), fields=[
            search.TextField(name='hashText', value=str(i)),
            search.TextField(name='keyId',value=str(key.id()))
            ])
            search.Index(name='myIndex').put(doc)
        #doc_index = search.Index(name='myIndex')
        #doc_index.delete('ahhzfmNsb3VkcHJvamVjdHRlc3QxLTEyNTJyKAsSBE1pbWUiCG1haW5FbnRpDAsSCVVzZXJJbWFnZRiAgICA4MGcCQw')
        #doc_index.delete('ahhzfmNsb3VkcHJvamVjdHRlc3QxLTEyNTJyKAsSBE1pbWUiCG1haW5FbnRpDAsSCVVzZXJJbWFnZRiAgICA4IuSCgw')





class ImagesPortal(webapp2.RequestHandler):
     def get(self):
        #Navigating to other page to read image
        self.response.write("""<!DOCTYPE HTML>
    <html lang="en">
    <head>
        <title>Image Portal</title>
        <link type="text/css" rel="stylesheet" href="/stylesheets/main.css" />
    </head>
    <body>
    <h1>5chan</h1>
    <div style="overflow-x:auto;">
    <table>""")

        greetings = UserImage.query(
            ancestor=image_key("mainEnti")) \
            .order(-UserImage.date) \
            .fetch(10)


        for greeting in greetings:
            self.response.write("<tr>")
            self.response.write('<td colspan="2"><img src="/img_serve?img_id=%s"></img></td>' % greeting.key.urlsafe() + '</tr>')
            self.response.write("<tr><td>"+greeting.author+"</td>")
            if greeting.caption:
                self.response.write("<td>"+greeting.caption+"</td>")
            if greeting.hash_Text:
                self.response.write("<td>"+greeting.hash_Text+"</td>")
            self.response.write("</tr>")
        self.response.write("</table></div>")
        user = users.get_current_user()
        if user:
            self.response.write(HTML_FORMS)
            self.response.write('<a href='+users.create_logout_url('/')+'>Logout</a>')
        else:
            self.response.write('<a href='+users.create_login_url('/')+'>Login</a>')
            self.response.write('</body></html>')


#Handler to read image into the <img> tag in the OUTPUT_HTML_PAGE
class ImageServe(webapp2.RequestHandler):
    def get(self):
        userImg_key = ndb.Key(urlsafe=self.request.get('img_id'))
        userImg= userImg_key.get()
        if userImg != None and userImg.imgData != None:
            self.response.headers['Content-Type'] = mimetypes.guess_type(userImg.file_name)[0]
            self.response.write(userImg.imgData)
        else:
            self.response.write('Error while fetching image data')


class ImageSearch(webapp2.RequestHandler):
    def post(self):
        imgObj = UserImage(id="mainEnti")
        imgObj = UserImage(parent=image_key("mainEnti"))

        index = search.Index(name="myIndex")
        textToSearch = self.request.get("textToSearch")
        query_str = "hashText : "+textToSearch
        search_query = search.Query(query_string=query_str,options=search.QueryOptions(returned_fields=['keyId']))

        try:
            results = index.search(search_query)
            self.response.write("""<!DOCTYPE HTML>
    <html lang="en">
    <head>
        <title>Searched Document</title>
        <link type="text/css" rel="stylesheet" href="/stylesheets/main.css" />
    </head>
    <body>
    <table>""")
            # Iterate over the documents in the results
            for scored_document in results:
                key_str = str(scored_document.doc_id).split('#')[0]
                #key_str = scored_document.doc_id
                #self.response.write('<h1>'+key_str+'</h1>')
                self.response.write("<tr>")
                self.response.write('<td colspan="2"><img src="/img_serve?img_id=%s"></img>' % key_str + '</tr>')
            self.response.write("</tr>")
            self.response.write("</table></div>")
            self.response.write('<a href="/">Go back to Image Portal</a>' )
            self.response.write("</body></html>")
        except search.Error:
            logging.exception('Search failed')

        #self.redirect('/')


class InviteFriendHandler(webapp2.RequestHandler):
    def post(self):
        user = users.get_current_user()
        if user is None:
          login_url = users.create_login_url(self.request.path)
          self.redirect(login_url)
          return
        to_addr = self.request.get("friend_email")
        if not mail.is_email_valid(to_addr):
            #ignore bad requests
            pass

        message = mail.EmailMessage()
        message.sender = user.email()
        message.to = to_addr
        message.body = """
I've invited you to 5chan!

To accept this invitation, click the following link,
or copy and paste the URL into your browser's address
bar:

http://%s.appspot.com
        """ % app_identity.get_application_id()

        message.send()
        self.redirect('/')


app = webapp2.WSGIApplication([
    ('/',ImagesPortal ),
    ('/img_upload',FileUpload),
    ('/img_serve',ImageServe),
    ('/img_search',ImageSearch),
    ('/invite', InviteFriendHandler),
    ], debug=True)
