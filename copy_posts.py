"""
Script to copy from source subreddit to dest subreddit
Used for testing
"""


import praw
from praw.models import MoreComments
from datetime import datetime, timedelta
import os
import shelve

reddit = praw.Reddit('MakeupFinderBot')
source = reddit.subreddit('muacjdiscussion')
dest = reddit.subreddit('MakeupFinderBot')

start_time = datetime.now() - timedelta(hours=24)
start_time = int(start_time.strftime('%s'))

if not os.path.exists('copied_objects.db'):
	with shelve.open('copied_objects') as new_shelve:
		new_shelve['submissions'] = []
		new_shelve['comments'] = []

with shelve.open('copied_objects') as copied_objects:
	copied_submissions = copied_objects['submissions']
	copied_comments = copied_objects['comments']

	for submission in source.submissions(start=start_time):
		if submission.id not in copied_objects['submissions']:
			# new_post = dest.submit(title=submission.title, selftext=submission.url, send_replies=False)
			print('Submission copied: ' + submission.title)
		# 	copied_submissions.append(submission.id)
		# 	copied_objects['submissions'] = copied_submissions

		# top_comments = submission.comments
		# if len(top_comments) == 0:
		# 	pass
		# for comment in top_comments:
		# 	if comment.id not in copied_objects['comments']:
		# 		# new_comment = new_post.reply(comment.body)
		# 		copied_comments.append(comment.id)
		# 		copied_objects['comments'] = copied_comments

