
from github import Github
import gspread
from oauth2client.service_account import ServiceAccountCredentials

CURR_MILESTONE = 1
POST_TO_ISSUE_1 = False

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

# FIXME:  Need to record actives and then check to see who is eligible from the full set
# This needs discussion as to the appropriate persistence mechanism

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
milestone = repo.get_milestone(CURR_MILESTONE)
issuelist = repo.get_issues(milestone=milestone)

report = []
report.append("## Results for %s" % milestone.title)
report.append("")
report.append("### Eligible Voters: %s" % len(trc_accounts))
report.append(" ".join(sorted(trc_accounts)))
report.append("")

active = {}
non_trc = {}

issues = list(issuelist)
issues.sort(key=lambda x: x.number)

for issue in issues:
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
		else:
			non_trc[who] = 1

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

	report.append("### Issue %s (%s)" % (issue.number, issue.title))
	report.append("  +1: %s [%s]" % (len(votes['+1']), ' '.join(sorted(votes['+1']))))
	report.append("   0: %s [%s]" % (len(votes['0']), ' '.join(sorted(votes['0']))))
	report.append("  -1: %s [%s]" % (len(votes['-1']), ' '.join(sorted(votes['-1']))))
	report.append("")

	for comment in comments:
		who = comment.user.login
		if who in trc_accounts:
			active[who] = 1

report.append("### Active on Issues")
active_accounts = sorted(active.keys())
report.append(" ".join(active_accounts))
report.append("")
report.append("### Inactive")
report.append(" ".join(sorted(list(set(trc_accounts) - set(active_accounts)))))
report.append("")
report.append("### Discarded as Ineligible")
report.append(" ".join(sorted(non_trc.keys())))

report_str = '\n'.join(report)

# milestone.edit(milestone.title, description=report_str)
# FIXME: milestone description doesn't support markdown
# so where to keep the report?

if POST_TO_ISSUE_1:
	issue = repo.get_issue(1)
	issue.create_comment(report_str)
else:
	print(report_str)
