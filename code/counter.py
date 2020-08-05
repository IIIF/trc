
from github import Github
import gspread
import sys
import standing
from oauth2client.service_account import ServiceAccountCredentials

# github lib is: https://pygithub.readthedocs.io/en/latest/
# gspread lib is: https://github.com/burnash/gspread
# Need to refactor away from gspread as it uses up teh quota pritty quickly.

# Change this to other milestones
CURR_MILESTONE = 12
POST_TO_ISSUES = True 

# Pull in list of github accounts from the registration spreadsheet
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('iiif-gspread-credentials.json', scope)
gc = gspread.authorize(credentials)
ss1 = gc.open_by_key('1YS7X6KOB2KytqAdxDjLqp54JHOW8KVT4CJv9ZIYOhas')
trc_accounts = standing.getTRCAccounts(ss1.get_worksheet(0))
activity = standing.buildStanding(ss1.get_worksheet(1), CURR_MILESTONE)

# Check all accounts are in standing list if not exit
missingEligable = set(trc_accounts.keys()) - set(activity.keys())
extraEligable = set(activity.keys()) - set(trc_accounts.keys())
if len(missingEligable) > 0:
    print ('To continue the following trc members need to have a row in the Eligability sheet:')
    for member in missingEligable:
        print (" * {} ".format(member))
    print ('The following can be removed as they are no longer part of the TRC:')
    for member in extraEligable:
        print (" * {} ".format(member))
    sys.exit()

(eligible, ineligible) = standing.getStatus(activity)

# Now configure github and repo
orgName = "iiif"
repoName = "trc"
userName = "glenrobson"
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
	voteNotEligable = {}
	for reaction in reactions:
		who = reaction.user.login
		if who in trc_accounts:
			trc_accounts[who] = "1"
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
				voteNotEligable[who] = 1
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
	issue_report.append("  Not TRC: %s [%s]" % (len(non_trc), ' '.join(sorted(non_trc))))
	issue_report.append("  Ineligible: %s [%s]" % (len(voteNotEligable), ' '.join(sorted(voteNotEligable))))
	issue_report.append("")


	against = len(votes['0']) + len(votes['-1'])
	favor = len(votes['+1'])
	issue_report.append("### Result: %s / %s = %0.2f" % (favor, against+favor, float(favor) / (against+favor)))
	if float(favor) / (against + favor) >= 0.6665:
		issue_report.append("Super majority is in favor, issue is approved")
		tag = "Approved"
	elif float(favor) / (against + favor) >= 0.5:
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
			trc_accounts[who] = "1"

active_accounts = []
for who in trc_accounts:
    if trc_accounts[who] == '1':
        active_accounts.append(who)

inactive_accounts = sorted(list(set(trc_accounts.keys()) - set(active_accounts)))

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

standing.updateStanding(ss1.get_worksheet(1), trc_accounts, activity, CURR_MILESTONE)
if POST_TO_ISSUES:
	issue = repo.get_issue(1)
	issue.create_comment(report_str)
else:
	print(report_str)

