from github import Github
import gspread
from gspread.exceptions import APIError
import sys
import time
from oauth2client.service_account import ServiceAccountCredentials


scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('iiif-gspread-credentials.json', scope)
gsheets = gspread.authorize(credentials)

def getRepo():
    orgName = "iiif"
    repoName = "trc"
    userName = "glenrobson"
    pwh = open("token.txt")
    pw = pwh.read().strip()
    pwh.close()
    gh = Github(userName, pw)
    return gh.get_repo("%s/%s" % (orgName, repoName))

def activtyFromMilestone(milestoneNo, trc_accounts):
    repo = getRepo()
    milestone = repo.get_milestone(milestoneNo)
    issuelist = repo.get_issues(milestone=milestone)

    for issue in issuelist:
        reactions = list(issue.get_reactions())
        comments = list(issue.get_comments())
        for reaction in reactions:
            if reaction.user.login in trc_accounts:
                trc_accounts[reaction.user.login] = "1"

        for comment in comments:
            if comment.user.login in trc_accounts:
                trc_accounts[comment.user.login] = "1"

def getTRCAccounts(sheet):
    sheet1 = sheet.get_all_values()
    trc_accouts_activity = {}
    for row in sheet1:
        if row[3] != '' and row[3] != 'Github':
            trc_accouts_activity[row[3]] = "0"
    return trc_accouts_activity

def getStatus(activity):
    eligible = {}
    ineligible = {}
    for person in activity:
        if activity[person]['status'] == '1':
            eligible[person] = True
        else:
            ineligible[person] = False
        

    return (eligible, ineligible)

def buildStanding(sheet, milestone):
    """
        This method reads the spreadsheet and stores all of the information in the following format:
        {
            "github_username": {
                "status": "1 or 0", # this is the eligability status
                "index": 1, # this is the row number in the spreadsheet
                "activity": [
                    '0','1','0','1'   # This is a list of milestones and if the user was active (1) or inactive (0)
                ]
            }
        }
    """
    sheet2 = sheet.get_all_values() # Efficient method with reduced API calls
    activity = {}
    activitySize = milestone
    if len(sheet2[0]) - 2 > milestone:
        activitySize = len(sheet2[0]) - 2
    rowNo = 2    
    for row in sheet2[1:]:
        activity[row[0]] = {
            "status": row[1],
            "activity": [''] * activitySize,
            "index": rowNo
        }
        rowNo += 1
        i = 0
        for cell in row[2:]:
            activity[row[0]]['activity'][i] = cell
            i += 1
    return activity

def updateEligibility(user, activity, sheet):
    activityCount = 0
    for value in activity['activity'][-3:]:
        if value is '':
            if activity['status'] == '0':
                print ('{} is a new TRC user so should be eligable ({})'.format(user, activity['activity'][-3:]))
                sheet.update_cell(int(activity["index"]), 2, '1')
            return    
        activityCount += int(value)
    if activity['status'] == '1' and activityCount == 0:
        print ("Changing {} to ineligibile. Current status {} Activity {}".format(user, activity['status'],activity['activity'][-3:]))
        sheet.update_cell(int(activity["index"]), 2, '0')
    elif activity['status'] == '0' and activityCount == 3:
        print ("Changing {} to eligibile. Current status {} Activity {}".format(user, activity['status'],activity['activity'][-3:]))
        sheet.update_cell(int(activity["index"]), 2, '1')

def updateStanding(sheet, trc_accouts_activity, activity, milestone):
    for person in trc_accouts_activity:
        if activity[person]['activity'][milestone - 1] == '':
            activity[person]['activity'][milestone -1] = trc_accouts_activity[person]
            while True:
                try:
                    cell = sheet.update_cell(int(activity[person]["index"]), milestone + 2, trc_accouts_activity[person])
                    updateEligibility(person, activity[person], sheet)
                    break
                except APIError as e:    
                    print ('Reached limit, waiting 2mins before retrying')
                    sleep(100)
                    cell = sheet2Obj.update_cell(int(activity[person]["index"]), milestone + 2, trc_accouts_activity[person])

        elif  activity[person]['activity'][milestone - 1] != trc_accouts_activity[person]:    
            print ('There is an existing value in {} milestone {} but latest count differes orig "{}" new "{}"'.format(person,milestone,activity[person]['activity'][milestone - 1], trc_accouts_activity[person]))


def sleep(length):                
    short_sleep = length / 10
    for i in range(10):
        print ('{} seconds to go'.format(int((10 - i) * short_sleep)))
        time.sleep(short_sleep)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print ("usage:\n\tpython3 standing.py [milestone_num]")
        sys.exit(-1)
    else:
        milestone = int(sys.argv[1])

    worksheet = gsheets.open_by_key('1YS7X6KOB2KytqAdxDjLqp54JHOW8KVT4CJv9ZIYOhas')

    # Get trc accounts with a default of 0 for no activity
    trc_accouts_activity = getTRCAccounts(worksheet.get_worksheet(0))
   
    # Update accounts which have either voted or commented to 1
    activtyFromMilestone(milestone, trc_accouts_activity)

    activity = buildStanding(worksheet.get_worksheet(1), milestone)
    
    updateStanding(worksheet.get_worksheet(1), trc_accouts_activity, activity, milestone)
    
