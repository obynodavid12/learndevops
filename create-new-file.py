import os 
# Create a new text file and add some content
with open('new1file.sh', 'w') as file:
    file.write('#!/bin/bash\n\nBUCKET=<BUCKETNAME>\n\nfor f in *.zip; do aws s3 cp $f s3://$BUCKET; done\n') 
# Check if the file has been created
print(os.listdir()) 
