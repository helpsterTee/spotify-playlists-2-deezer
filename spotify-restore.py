import argparse
import json
import sys
import re
import urwid
import http.client
import http.server
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

## CHANGE THESE VALUES
APPID='12345'
SECRET='yoursecretsecret'
## DO NOT CHANGE ANYTHING BELOW HERE

PORT=23412
_PLAYLIST_IMPORT = "Playlists to import"
playlist_names = []
selected_playlists = set()
deezer_playlists = []
longest_playlistcount = -1
jsoncont = {}
listitems = []
shouldparse = False
token = ""

## UI Classes
'''
	A Frame that allows to switch focus from head, body and footer with the tab key
'''
class TabFrame(urwid.Frame):
	def keypress(self, size, key):
		"""Pass keypress to widget in focus, except when it's tab"""
		(maxcol, maxrow) = size

		if key == 'tab':
			if self.focus_part == 'header':
				self.focus_part = 'body'
				self._invalidate()
				return key
			elif self.focus_part == 'body':
				self.focus_part = 'footer'
				self._invalidate()
				return key
			elif self.focus_part == 'footer':
				self.focus_part = 'header'
				self._invalidate()
				return key

		if self.focus_part == 'header' and self.header is not None:
			if not self.header.selectable():
				return key
			return self.header.keypress((maxcol,),key)
		if self.focus_part == 'footer' and self.footer is not None:
			if not self.footer.selectable():
				return key
			return self.footer.keypress((maxcol,),key)
		if self.focus_part != 'body':
			return key
		remaining = maxrow
		if self.header is not None:
			remaining -= self.header.rows((maxcol,))
		if self.footer is not None:
			remaining -= self.footer.rows((maxcol,))
		if remaining <= 0: return key

		if not self.body.selectable():
			return key
		return self.body.keypress( (maxcol, remaining), key )

## UI code
'''
	Main Menu
'''
def menu(title, choices):
	body = [urwid.Text(title), urwid.Text('The longest playlist has '+str(longest_playlistcount)+' entries. Do you want to modify the selection or start the import?') ,urwid.Divider()]
	for c in choices:
		button = urwid.Button(c)
		urwid.connect_signal(button, 'click', item_chosen, c)
		body.append(urwid.AttrMap(button, None, focus_map='reversed'))
	return urwid.ListBox(urwid.SimpleFocusListWalker(body))

# check if the checkbox should be selected
def is_selected(position):
	return position in selected_playlists

# callback for selecting / deselecting
def checkbox_callback(checkbox, state, id_):
	if state:
		selected_playlists.add(id_)
	else:
		selected_playlists.discard(id_)

# jump back to the menu
def showmenu(button):
	start.original_widget = urwid.Padding(menu(u'Spotify2Deezer', ['Modify Selection of Playlists', 'Import to Deezer', 'Quit']), left=2, right=2)

# select all playlists
def select_all(button):
	selected_playlists.clear()
	for plist in playlist_names:
		selected_playlists.add(plist['id'])
	playlistitems(_PLAYLIST_IMPORT)
# deselect all playlists
def deselect_all(button):
	selected_playlists.clear()
	playlistitems(_PLAYLIST_IMPORT)

# create the selection view of playlists
def playlistitems(title):
	global listitems
	bt_sv = urwid.Button("Save")
	urwid.connect_signal(bt_sv, 'click', showmenu)
	bt_ca = urwid.Button("Cancel")
	urwid.connect_signal(bt_ca, 'click', showmenu)
	bt_sa = urwid.Button("Select all")
	urwid.connect_signal(bt_sa, 'click', select_all)
	bt_da = urwid.Button("Deselect all")
	urwid.connect_signal(bt_da, 'click', deselect_all)
	footer = urwid.Columns([bt_sv, bt_sa, bt_da, bt_ca], 1)
	items = []
	for item in playlist_names:
		items.append(urwid.CheckBox(item['name'], is_selected(item['id']), on_state_change=checkbox_callback, user_data=item['id']))
	start.original_widget = TabFrame(urwid.ListBox(urwid.SimpleListWalker(items)), header=urwid.Text("Select Playlists"), footer=footer, focus_part='body')

# main menu button handler
def item_chosen(button, choice):
	done = urwid.Button(u'Ok')

	if choice == 'Modify Selection of Playlists':
		playlistitems(_PLAYLIST_IMPORT)
		urwid.connect_signal(done, 'click', exit_program)
	elif choice == 'Quit':
		exit_program(button)
	elif choice == 'Import to Deezer':
		authorize()

def exit_program(button):
	raise urwid.ExitMainLoop()

## Authorize code
def authorize():
	webbrowser.open('https://connect.deezer.com/oauth/auth.php?' + urllib.parse.urlencode({
		'app_id': APPID,
		'redirect_uri': 'http://127.0.0.1:{}/authfinish'.format(PORT),
		'perms': 'basic_access,manage_library'
	}))

	# Start a simple, local HTTP server to listen for the authorization token... (i.e. a hack).
	server = _AuthorizationServer('127.0.0.1', PORT)
	try:
		while True:
			server.handle_request()
	except _Authorization as auth:
		get_actual_token(auth.access_token)

class _AuthorizationServer(http.server.HTTPServer):
	def __init__(self, host, port):
		http.server.HTTPServer.__init__(self, (host, port), _AuthorizationHandler)

	# Disable the default error handling.
	def handle_error(self, request, client_address):
		raise

class _AuthorizationHandler(http.server.BaseHTTPRequestHandler):
	def do_GET(self):
		# Read access_token and use an exception to kill the server listening...
		if self.path.startswith('/authfinish?'):
			self.send_response(200)
			self.send_header('Content-Type', 'text/html')
			self.end_headers()
			self.wfile.write(b'<script>close()</script>Thanks! You may now close this window.')
			raise _Authorization(re.search('code=([^&]*)', self.path).group(1))

		else:
			self.send_error(404)

	# Disable the default logging.
	def log_message(self, format, *args):
		pass

class _Authorization(Exception):
	def __init__(self, access_token):
		self.access_token = access_token

# the other one is actually a "code", so now get the real token
def get_actual_token(code):
	global token, shouldparse
	f = urllib.request.urlopen("https://connect.deezer.com/oauth/access_token.php?app_id="+APPID+"&secret="+SECRET+"&code="+code)
	fstr = f.read().decode('utf-8')

	if len(fstr.split('&')) != 2:
		raise urwid.ExitMainLoop()

	stri = fstr.split('&')[0].split('=')[1]
	token = stri
	shouldparse = True
	raise urwid.ExitMainLoop()

'''
	Add a playlist to Deezer with name
	return playlist ID
'''
def add_playlist(name):
	params = urllib.parse.urlencode({'title':name}).encode('UTF-8')
	url = 'https://api.deezer.com/user/me/playlists?access_token='+token
	f = urllib.request.urlopen(url, data=params)
	fstr = f.read().decode('utf-8')
	js = json.loads(fstr)
	if 'id' not in js:
		return -1
	else:
		return js['id']

'''
	Search a track on Deezer by ISRC number
	return Deezer ID of track
'''
def search_track(id):
	try:
		url = 'https://api.deezer.com/track/isrc:'+id+'?access_token='+token
		f = urllib.request.urlopen(url)
		fstr = f.read().decode('utf-8')
		js = json.loads(fstr)
		if 'error' in js:
			return -1
		else:
			return js['id']
	except:
		return -1

'''
	Get the user's Deezer playlists to prevent double entries. Will recusively fetch more, as they are limited to about 35 lists per call.
	return titles of existing playlists (yadda, yadda, string compare, I know...)
'''
def get_deezer_playlists(next):
	url = ''
	existing = []
	if next == -1:
		url = 'https://api.deezer.com/user/me/playlists?access_token='+token

	else:
		url = next

	f = urllib.request.urlopen(url)
	fstr = f.read().decode('utf-8')
	js = json.loads(fstr)
	if 'data' not in js:
		return -1
	else:
		existing = []
		for d in js['data']:
			existing.append(d['title'])
		if 'next' in js:
			existing.extend(get_deezer_playlists(js['next']+'?access_token='+token))
		return existing

'''
	Batch add tracks to a Deezer playlist with <playlistid>
	return 1 if okay, -1 if not
'''
def add_tracks(playlistid, tracklist):
	strlist = ','.join(str(e) for e in tracklist)
	params = urllib.parse.urlencode({'songs':strlist}).encode('UTF-8')
	url = 'https://api.deezer.com/playlist/'+str(playlistid)+'/tracks?access_token='+token
	f = urllib.request.urlopen(url, data=params)
	fstr = f.read().decode('utf-8')
	if fstr == "true":
		return 1
	else:
		return -1

'''
	WORK IT HARDER
		MAKE IT BETTER
			DO IT FASTER
				MAKES US STRONGER
'''
def start_import():
	# work work, gotta work!
	print("Importing "+str(len(selected_playlists))+ " playlist(s) to Deezer")
	existing_lists = get_deezer_playlists(-1)

	for li in jsoncont:
		if li['id'] in selected_playlists:
			#only use selected Playlists that do not exist on deezer
			should_continue = True
			for exli in existing_lists:
				if exli in li['name']:
					should_continue = False
					break
			if should_continue == False:
				print("# Skipping list "+li['name']+" because it already exists at Deezer!")
				continue

			track_ids = []
			for trk in li['tracks']:
				if 'isrc' not in trk['track']['external_ids']:
					continue

				trid = search_track(trk['track']['external_ids']['isrc'])
				if trid > -1:
					track_ids.append(trid)
					print("+ Found track "+trk['track']['name'])
				else:
					print("- Unavailable track "+trk['track']['name']+" ["+trk['track']['external_ids']['isrc']+"]")

			if len(track_ids) > 0:
				print("Creating playlist "+li['name']+" ...")
				id_ = add_playlist(li['name'])

				if id_ == -1:
					continue

				resp = add_tracks(id_, track_ids)
				if resp == -1:
					print("! Error adding tracks")
				else:
					print("Added "+str(len(track_ids))+" tracks to "+li['name'])
	print("~~ Finished! ~~")

'''
	Reads the file from disk
'''
def readfile():
	global longest_playlistcount, jsoncont
	parser = argparse.ArgumentParser(description='Imports your Spotify playlists to Deezer. By default, opens a browser window '
		+ 'to authorize the Deezer Web API')
	parser.add_argument('file', help='output filename', nargs='?')
	args = parser.parse_args()

	with (open(args.file, 'r', encoding='utf-8')) as f:
		line = f.readline()
		jsoncont = json.loads(line)
		#print(jsoncont[0].keys())
		#print(jsoncont[0]['name'])
		#print(jsoncont[0]['tracks'][0].keys())
		#print(jsoncont[0]['tracks'][0]['track'].keys())

		for plist in jsoncont:
			playlist_names.append({'name':plist['name'], 'id':plist['id'], 'count':len(plist['tracks'])})
			selected_playlists.add(plist['id'])
			if len(plist['tracks']) > longest_playlistcount:
				longest_playlistcount = len(plist['tracks'])

if __name__ == '__main__':
	readfile()
	start = urwid.Padding(menu(u'Spotify2Deezer', ['Modify Selection of Playlists', 'Import to Deezer', 'Quit']), left=2, right=2)
	top = urwid.Overlay(start, urwid.SolidFill(u'\N{MEDIUM SHADE}'),
		align='center', width=('relative', 60),
		valign='middle', height=('relative', 60),
		min_width=20, min_height=9)
	loop = urwid.MainLoop(top, palette=[('reversed', 'standout', '')]).run()
	if shouldparse:
		start_import()
	else:
		print("Error authenticating. Try again!")
