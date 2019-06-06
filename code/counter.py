
from github import Github
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# github lib is: https://pygithub.readthedocs.io/en/latest/
# gspread lib is: https://github.com/burnash/gspread


CURR_MILESTONE = 5
POST_TO_ISSUES = False

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

sheet2 = ss1.get_worksheet(1)
e_accounts = sheet2.col_values(1)
e_okay = sheet2.col_values(2)
eligibility = dict(zip(e_accounts, e_okay))
if 'Name' in eligibility:
	del eligibility['Name']
if '' in eligibility:
	del eligibility['']
if 'total eligible:' in eligibility:
	del eligibility['total eligible:']

for (k,v) in eligibility.items():
	eligibility[k] = bool(int(v))

eligible = [x for (x,y) in eligibility.items() if y]
eligible.sort()
ineligible = [x for (x,y) in eligibility.items() if not y]

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
report.append("### Eligible Voters: %s" % len(eligible))
report.append(" ".join(eligible))
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
			if who in eligible:
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

	issue_report = []
	issue_report.append("### Issue %s (%s)" % (issue.number, issue.title))
	issue_report.append("  +1: %s [%s]" % (len(votes['+1']), ' '.join(sorted(votes['+1']))))
	issue_report.append("   0: %s [%s]" % (len(votes['0']), ' '.join(sorted(votes['0']))))
	issue_report.append("  -1: %s [%s]" % (len(votes['-1']), ' '.join(sorted(votes['-1']))))
	issue_report.append("")


	against = len(votes['0']) + len(votes['-1'])
	favor = len(votes['+1'])
	issue_report.append("### Result: %s / %s = %0.2f" % (favor, against+favor, float(favor) / (against+favor)))
	if float(favor) / (against + favor) > 0.65:
		issue_report.append("Super majority is in favor, issue is approved")
		tag = "Approved"
	elif float(favor) / (against + favor) > 0.49:
		issue_report.append("No super majority, issue is referred to ex officio for decision")
		tag = "Ex Officio Decision"
	else:
		issue_report.append("Issue is rejected")
		tag = "Rejected"

	if POST_TO_ISSUES:
		issue_report_str = "\n".join(issue_report)
		issue.create_comment(issue_report_str)
		issue.add_to_labels(tag)

	report.extend(issue_report)
	report.append("")

	for comment in comments:
		who = comment.user.login
		if who in trc_accounts:
			active[who] = 1

active_accounts = sorted(active.keys())
inactive_accounts = sorted(list(set(trc_accounts) - set(active_accounts)))

report.append("### Active on Issues")
report.append(" ".join(active_accounts))
report.append("")
report.append("### Inactive")
report.append(" ".join(inactive_accounts))
report.append("")
report.append("### Discarded as Ineligible")
report.append(" ".join(sorted(non_trc.keys())))
report.append(" ".join(sorted(ineligible)))
report_str = '\n'.join(report)

if POST_TO_ISSUES:
	issue = repo.get_issue(1)
	issue.create_comment(report_str)

	# find column for milestone in sheet2
	headers = sheet2.row_values(1)
	col = 1
	for h in headers:
		if h.isdigit() and int(h) == CURR_MILESTONE:
			break
		else:
			col += 1

	# Now walk through accounts and set column in ss
	row = 0
	for acc in e_accounts:
		row += 1	
		#print(acc)
		if acc in active_accounts:
			# set to 1
			cell = sheet2.cell(row, col)
			#print("%s to %s" % (cell.value, 1))
			cell.value = 1
		elif acc in inactive_accounts:
			cell = sheet2.cell(row, col)
			#print("%s to %s" % (cell.value, 0))
			cell.value = 0
		else:
			# header row
			continue

		# And now update eligibility
		valso = sheet2.row_values(row)
		vals = [int(x) for x in valso[2:]]
		acco = valso[0]
		if acco != acc:
			print("Uh-oh, order seems to have changed, bailing out")
			raise

		standing = 1
		window = [1, vals[0], vals[1]]
		for v in vals[2:]:
			window = [window[1], window[2], v]
			if standing == 1 and sum(window) == 0:
				print("Setting %s to bad standing due to %s" % (acc, vals))
				standing = 0
			elif standing == 0 and sum(window) == 3:
				print("Setting %s to good standing due to %s" % (acc,vals))
				standing = 1
		cell = sheet2.cell(row, 2)
		cell.value = standing

else:
	print(report_str)

