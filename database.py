import peewee as pw
import os
import random
import string
import datetime

CONTENT_DIR = '/content'
TEMP_DIR = '/content/temp'

DEPTH = 2
WIDTH = 2
WEB_NAME_LEN = 6

def get_content_dir(hash):
    '''
    Generate the path to a directory for a given hash, and create it.

    For example, if you have a hash "abcdefghijklmno"
    and the default DEPTH=2 and WIDTH=2,
    then this will return "/content/ab/abcd" and create it.
    '''
    dirs = [CONTENT_DIR]
    for cur_depth in range(DEPTH):
        cur_depth += 1
        dirs.append(hash[:WIDTH*cur_depth])
    dir = os.path.join(*dirs)
    os.makedirs(dir, exist_ok=True)
    return dir


db = pw.SqliteDatabase('/file-data.db')

class MyModel(pw.Model):
    class Meta:
        database = db

def create_table(cls):
    db.create_tables([cls])
    return cls

@create_table
class File(MyModel):
    file_active = pw.BooleanField(default=True)
    file_present_in_filesystem = pw.BooleanField(default=True)

    web_name = pw.CharField(index=True)
    extension = pw.CharField()
    mime_type = pw.CharField(null=True)
    sha256 = pw.CharField(index=True)
    size = pw.IntegerField(index=True)

    uploaded_at = pw.DateTimeField(default=datetime.datetime.now)
    uploader_ip = pw.IPField(null=True)
    expires_at = pw.DateTimeField(null=True)

    def get_path_to_file(self):
        '''
        Return the path where this file appears to be stored.
        '''
        return get_content_dir(self.sha256) + '/' + self.sha256 + '.' + self.extension

    @staticmethod
    def generate_web_name(trials=10):
        '''
        Generate a random web-safe string for "web_facing_name" not in use yet.
        If it takes too many trials to get an unused string, return None.
        '''
        available_chars = string.ascii_letters + string.digits
        for _ in range(trials):
            test_str = []
            for _ in range(WEB_NAME_LEN):
                test_str.append(random.choice(available_chars))
            test_str = ''.join(test_str)
            if File.select(pw.fn.count(1)).where(File.web_name == test_str).scalar() > 0:
                continue
            else:
                return test_str
            
            
            

