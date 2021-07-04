'''
@author zer0eXploit

Upload files inside a directory to onedrive.
Needs access token for the file upload to work.
Access token is obtained by authenticating at the following url.
Replace client_id, required_scopes=[files.readwrite.all] and redirect_uri with own's values attained from Azure.
https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id={}&scope={}&response_type=token&redirect_uri={}

'''

import os
import requests
import traceback
from datetime import datetime


def upload_to_onedrive(access_token, folder_path):
    headers = {'Authorization': f'Bearer {access_token}'}

    # Access files in the folder and sub folders
    for root, _dirs, files in os.walk(folder_path):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            file_size = os.stat(file_path).st_size

            if file_size < 4100000:
                # Perform is simple upload to the API
                normal_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{root}/{file_name}:/content"
                with open(f'{file_path}', 'rb') as f:
                    requests.put(normal_url, data=f, headers=headers)
                continue

            # file size more than 4.1MB, so create upload session and get upload url
            url = f'https://graph.microsoft.com/v1.0/me/drive/root:/{root}/{file_name}:/createUploadSession'
            payload = {
                "item": {
                    "@odata.type": "microsoft.graph.driveItemUploadableProperties",
                    "@microsoft.graph.conflictBehavior": "rename",
                    "name": f"{file_name}"
                }
            }
            response = requests.post(url, headers=headers, params=payload)

            if response.status_code == requests.codes.ok:
                upload_url = response.json()['uploadUrl']
                print(f'Uploading: {file_name} - {file_size//1048576} MB.')

                try:
                    # IMPORTANT! Reduce chunk size if memory capacity is limited.
                    chunk_size = 62914560  # 60 mebibytes.
                    total_chunks = file_size//chunk_size  # total chunks, get the floor
                    chunk_leftover = file_size - chunk_size * total_chunks

                    t1 = datetime.now()

                    with open(f'{file_path}', 'rb') as f:
                        i = 0
                        chunk = f.read(chunk_size)
                        while chunk:
                            start = i*chunk_size
                            end = start + chunk_size

                            # because total chunks is taken floor, there are bytes left to read,
                            # that is when i equals the number of chunks as i starts at 0.
                            if i == total_chunks:
                                end = start + chunk_leftover

                            u_h = {
                                'Content-Length': f'{chunk_size}',
                                'Content-Range': f'bytes {start}-{end-1}/{file_size}'
                            }

                            # do chunk upload
                            requests.put(upload_url, data=chunk, headers=u_h)

                            chunk = f.read(chunk_size)
                            i += 1

                    t2 = datetime.now()
                    print(f'Done Uploading: {file_name}.')
                    print(f'Duration: {(t2-t1).total_seconds()/60} min(s).')

                except Exception:
                    traceback.print_exc()
                    print("Error Uploading {file_name}")

            else:
                if response.status_code == 401:
                    # token expired or invalid
                    access_token = input('Please enter new token.')
                else:
                    # Error creating upload session
                    print(response.json())
