import sys

GITHUB_OAUTH_KEY=""
GITHUB_OAUTH_SECRET=""


try:
	from local_settings import *
except ImportError, e:
	sys.stderr.write("Error: You haven't defined local settings. Create a local_settings.py\n")
	raise