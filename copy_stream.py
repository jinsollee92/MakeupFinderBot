"""
Script to copy from source subreddit to dest subreddit using stream
Used for testing
"""

import praw
import time

reddit = praw.Reddit('MakeupFinderBotTest')
source = reddit.subreddit('muacjdiscussion')
dest = reddit.subreddit('MakeupFinderBot')

ignore = 0
post = reddit.submission(id='63hra9')

while True:
	for comment in source.stream.comments():
		# ignore the first 100
		if ignore < 100:
			ignore += 1
		else:
			print(comment.body)
			post.reply(comment.body)

			time.sleep(15)