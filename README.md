# gas-framework
An enhanced web framework (based on [Flask](http://flask.pocoo.org/)) for use in the capstone project. Adds robust user authentication (via [Globus Auth](https://docs.globus.org/api/auth)), modular templates, and some simple styling based on [Bootstrap](http://getbootstrap.com/).

Directory contents are as follows:
* `/web` - The GAS web app files
* `/ann` - Annotator files
* `/util` - Utility scripts for notifications, archival, and restoration
* `/aws` - AWS user data files

## Archive Process
1. The archive process is as follows: 
    1. In `ann/run.py` after running the annotation job, as its last step the system checks to see if the user was a _free_user_. If so, then it uses `SQS` to send a message to the SQS queue `jmidkiff_archive`, otherwise nothing more happens. This queue has a default delay of 5 minutes, so no message will be delivered to it before that time has elapsed. 
    2. The `util/archive/archive.py` script is continuously running and checking the `jmidkiff_archive` queue for any jobs that should be archived. If it receives a message, it checks what type of user does this _user_id_ belong to. 
        * If the user is a _premium_user_ according to the database, the script deletes the message and nothing happens, which accounts for the edge case where a user upgrades from free to premium after they submit an annotation job and before their results are archived. 
        * Otherwise the user is a _free_user_, and the script performs the following actions: 
            1. Get the results file from S3
            2. Upload that bytes-file archive to Glacier
            3. Update the dynamodb entry for this job to add _results_file_archive_id_ and delete _s3_key_result_file_
            4. Delete the results file from S3
            5. And finally, delete the message from `jmidkiff_archive`. This leaves open the possibility that a user will downgrade their premium account to a free account. Logically this would mean that all of the user's _result_files_ should be uploaded to glacier, but this feature will have to be added later.

## Restore Process
1. The restore process is as follows: 
    1. In `web/views.py`, the endpoint "/subscribe" will send a POST request to update the user's profile, which triggers `SQS` to send a message to the queue `jmidkiff_restore`. 
    2. `util/restore/restore.py` continuously waits to receive messages from this queue, and when it receives one it: 
        1. If the user is a _free_user_, skip to number 4. 
        2. If the user is a _premium_user_, then it uses `dynamodb.query()` to get every annotation job record that the user has submitted and that has been archived to glacier. Specifically, these records will 
            1. Not have an _s3_key_result_file_ listed, and
            2. Have a _results_file_archive_id_ listed.
        3. For each of these _results_file_archive_ids_, we will initiate a job for _archive_retrieval_ on `glacier`, with the `SNSTopic` `jmidkiff_job_thaw` attached. This will prompt `jmidkiff_job_thaw` to publish a message when each of those jobs has been completed. 
            * In this script, `glacier.initiate_job()` will default to expedited retrieval, but if this leads to `InsufficientCapacityException`, the function will re-run with standard retrieval. 
        4. The message is deleted from `jmidkiff_restore`.  
    3. The script `thaw.py` is waiting with the queue `jmidkiff_thaw` which is subscribed to the `SNS` topic `jmidkiff_job_thaw`. When it receives a message that a job has been completed, it will: 
        1. Use the `glacier` _JobId_ included in the message to receive the bytes-file that was un-archived. 
        2. Use `dynamodb.scan()` to locate the record where `results_file_archive_id = ArchiveId`, gather several fields from that observation, and properly concatenate them to form the _s3_key_result_file_ name. 
        3. Puts the bytes-file back up to `S3` with the _s3_key_result_file_ name
        4. Updates the corresponding `dynamodb` record to delete the _results_file_archive_id_ field and add the _s3_key_results_file_ field. 
        5. Deletes the message from the `jmidkiff_thaw` queue. 

## Additional Notes: 
* I included the `anntools` repository at `/home/ec2-user/mpcs-cc/gas/ann/anntools` in order for `ann/run.py` to work. 
* Things I would do if I had more time before the deadline: 
    * Perform auto-scaling exercises with `Locust`
    * Change error-handling to write to logs
    * Increase use of functions (more like how I wrote `thaw.py` rather than how I wrote `restore.py`)
