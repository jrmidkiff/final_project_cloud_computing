This directory should contain the following utility-related files:
* `helpers.py` - Miscellaneous helper functions
* `util_config.py` - Common configuration options for all utilities

Each utility should be in its own sub-directory, along with its configuration file, as follows:

/archive
* `archive.py` - Archives free user result files to Glacier
* `archive_config.ini` - Configuration options for archive utility

/notify
* `notify.py` - Sends notification email on completion of annotation job
* `notify_config.ini` - Configuration options for notification utility

/restore
* `restore.py` - Initiates restore of Glacier archive(s)
* `restore_config.ini` - Configuration options for restore utility

/thaw
* `thaw.py` - Saves recently restored archive(s) to S3
* `thaw_config.ini` - Configuration options for thaw utility

If you completed Ex. 14, include your annotator load testing script here
* `ann_load.py` - Annotator load testing script