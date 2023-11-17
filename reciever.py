import socket
import threading
import subprocess
import os
import time

# Define the host and port to listen on
host = "このソフトウェアを配置するサーバのIPアドレス"
port = 1234

# Initialize variables to track the maximum value and its associated project and task
max_value = float('-inf')  # Initialize with negative infinity
max_project = None
max_task = None

# Lock to ensure thread-safe access to max_value, max_project, and max_task
data_lock = threading.Lock()

# Dictionary to store received data and associated process IDs
received_data_and_process = {}

# Function to handle data from a client and update max_value, max_project, and max_task
def handle_client(conn, addr):
    global max_value, max_project, max_task
    rsync_parent_id = None
    rsync_process_id = None
    max_client_addr = None
    received_data_dict = None  # Initialize received_data_dict

    with conn:
        while True:
            # Receive data from the client
            data = conn.recv(1024)  # Adjust the buffer size as needed

            if not data:
                break  # No more data, break the loop

            # Deserialize the received data
            received_data_str = data.decode('utf-8')
            received_data_dict = eval(received_data_str)  # Assuming the data is a dictionary

            # Compare the received data with the current maximum
            received_duration = received_data_dict.get('duration')
            if received_duration is not None:
                with data_lock:
                    if received_duration > max_value:
                        max_value = received_duration
                        max_project = received_data_dict.get('project')
                        max_task = received_data_dict.get('task')
                        max_client_addr = addr

                # Update the received data for the current client
                with data_lock:
                    received_data_and_process[addr] = received_data_dict
                    rsync_parent_id = received_data_dict.get('rsync_parent_id')
                    rsync_process_id = received_data_dict.get('rsync_process_id')

            print(f"Received data from {addr}: {received_data_dict}")
            print(f"Maximum duration received is {max_value} for Project '{max_project}' and Task '{max_task}'.")

            # Kill processes for clients with values less than the maximum
            for client_addr, data in received_data_and_process.items():
                if client_addr != max_client_addr:
                    # Get the process IDs from the received data (modify this as per your data structure)
                    rsync_parent_id = data.get('rsync_parent_id')
                    rsync_process_id = data.get('rsync_process_id')
                    ip_addr = client_addr[0]

                    if rsync_parent_id:
                        remote_server = f"mikami@{ip_addr}"  # リモートサーバのユーザー名とホスト名を指定
                        remote_command = f"ssh {remote_server} pkill -STOP -P {rsync_parent_id}"
                        try:
                            subprocess.run(remote_command, shell=True, check=True)
                            print(f"親：Stopped process for {ip_addr} on remote server.")
                        except subprocess.CalledProcessError as e:
                            print(f"Error stopping process on remote server: {e}")

                    if rsync_process_id:
                        remote_server = f"mikami@{ip_addr}"  # リモートサーバのユーザー名とホスト名を指定
                        remote_command = f"ssh {remote_server} pkill -STOP -P {rsync_process_id}"
                        try:
                            subprocess.run(remote_command, shell=True, check=True)
                            print(f"子：Stopped process for {ip_addr} on remote server.")
                        except subprocess.CalledProcessError as e:
                            print(f"Error stopping process on remote server: {e}")

    # Check the directory for interrupted transfers using received_data_dict
    check_directory(ip_addr, received_data_dict, rsync_parent_id, rsync_process_id)

# Function to check the directory for interrupted transfers
def check_directory(ip_addr, received_data_dict, rsync_parent_id, rsync_process_id):
    target_directory = "you-sendで指定したファイルが届く場所の絶対パス"  # Set the path to the target directory
    selected_file = received_data_dict.get('select_file')

    while selected_file:
        if selected_file in os.listdir(target_directory):
            print(f"File found in directory: {addr}")

            # Extract the process IDs for the parent and child processes
            if rsync_parent_id and rsync_process_id:
                remote_server = f"ユーザ名@{ip_addr}"  # Set the remote server's username and hostname
                parent_resume_command = f"ssh {remote_server} pkill -CONT -P {rsync_parent_id}"
                child_resume_command = f"ssh {remote_server} pkill -CONT -P {rsync_process_id}"

                try:
                    # Resume both the parent and child processes
                    subprocess.run(parent_resume_command, shell=True, check=True)
                    subprocess.run(child_resume_command, shell=True, check=True)
                    print(f"Resumed the interrupted file transfer for {ip_addr}")
                except subprocess.CalledProcessError as e:
                    print(f"Error resuming the file transfer on the remote server: {e}")

            break  # Exit the loop when the file is found
        time.sleep(1)  # Check every 1 second

# Create a socket server to listen for incoming connections
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
    server_socket.bind((host, port))
    server_socket.listen()
    print(f"Listening on {host}:{port}...")

    while True:
        # Accept incoming connections
        conn, addr = server_socket.accept()
        print(f"Connection from {addr}")

        max_client_addr = None  # Initialize max_client_addr

        # Create a new thread to handle the client
        client_thread = threading.Thread(target=handle_client, args=(conn, addr))
        client_thread.start()
