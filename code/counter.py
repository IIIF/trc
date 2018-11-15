
from github import Github
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Pull in list of github accounts from the registration spreadsheet
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('iiif-gspread-credentials.json', scope)
gc = gspread.authorize(credentials)
ss1 = gc.open_by_key('1YS7X6KOB2KytqAdxDjLqp54JHOW8KVT4CJv9ZIYOhas')
sheet = ss1.get_worksheet(0)
trc_accounts = set(sheet.col_values(4))
trc_accounts.remove('')
trc_accounts.remove('Github')

# Now configure github and repo
orgName = "iiif"
repoName = "trc"
userName = "azaroth42"
pwh = open("token.txt")
pw = pwh.read().strip()
pwh.close()
gh = Github(userName, pw)
repo = gh.get_repo("%s/%s" % (orgName, repoName))

# Find the issues for the current call

CURR_MILESTONE = 1
milestone = repo.get_milestone(CURR_MILESTONE)
issuelist = repo.get_issues(milestone=milestone)

active = {}

for issue in list(issuelist):
	reactions = list(issue.get_reactions())
	comments = list(issue.get_comments())

	votes = {'+1': set(), '-1': set(), '0': set()}

	for reaction in reactions:
		who = reaction.user.login
		if who in trc_accounts:
			active[who] = 1
			which = reaction.content  
			# Agree: '+1' Disagree: '-1' +0: 'confused'
			# Allow 'heart' as synonym for '+1' 
			if which == 'confused':
				which = '0'
			elif which == 'heart':
				which = '+1'
			if which in votes:
				votes[which].add(who)

	# invalid state:
	#   same user casting multiple votes
	#   discard all votes and make a note
	dupes = set()
	dupes.update(votes['+1'].intersection(votes['-1']))
	dupes.update(votes['+1'].intersection(votes['0']))	
	dupes.update(votes['0'].intersection(votes['-1']))

	for vv in votes.values():
		for d in dupes:
			if d in vv:
				vv.remove(d)

	print(issue.number, votes)

	for comment in comments:
		who = comment.user.login
		if who in trc_accounts:
			active[who] = 1

print(active)
