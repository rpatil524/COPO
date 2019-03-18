# THIS CODE MOVED TO enaSubmission.py


from datetime import datetime
import pexpect
import os

from dal.copo_da import RemoteDataFile


def do_aspera_transfer(transfer_token=None, user_name=None, password=None, remote_path=None, file_path=None,
                       path2library=None):
    cmd = "./ascp -d -QT -l300M -L- {file_path!s} {user_name!s}:{remote_path!s}".format(**locals())
    os.chdir(path2library)

    thread = pexpect.spawn(cmd, timeout=None)
    thread.expect(["assword:", pexpect.EOF])
    thread.sendline(password)

    cpl = thread.compile_pattern_list([pexpect.EOF, '(.+)'])

    while True:
        i = thread.expect_list(cpl, timeout=None)
        if i == 0:  # EOF! Possible error point if encountered before transfer completion
            print("Process termination - check exit status!")
            break
        elif i == 1:
            pexp_match = thread.match.group(1)

            file_name = file_path.split('/')[-1]
            tokens_to_match = [file_name, "Mb/s"]
            units_to_match = ["KB", "MB"]
            time_units = ['d', 'h', 'm', 's']
            end_of_transfer = False

            if all(tm in pexp_match.decode("utf-8") for tm in tokens_to_match):
                fields = {
                    "transfer_status": "transferring",
                    "current_time": datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                }

                tokens = pexp_match.decode("utf-8").split(" ")
                for token in tokens:
                    if not token == '':
                        if '%' in token:
                            fields['pct_completed'] = token.rstrip("%")
                            # flag end of transfer
                            print(str(transfer_token) + " " + token)
                            if token.rstrip("%") == 100:
                                end_of_transfer = True
                        elif any(um in token for um in units_to_match):
                            fields['bytes_transferred'] = token
                        elif "Mb/s" in token:
                            fields['transfer_rate'] = token
                        elif "status" in token:
                            fields['transfer_status'] = token.split('=')[-1]
                        elif "rate" in token:
                            fields['transfer_rate'] = token.split('=')[-1]
                        elif "elapsed" in token:
                            fields['elapsed_time'] = token.split('=')[-1]
                        elif "loss" in token:
                            fields['bytes_lost'] = token.split('=')[-1]
                        elif "size" in token:
                            fields['file_size_bytes'] = token.split('=')[-1]
                        elif "file" in token:
                            fields['file_path'] = token.split('=')[-1]
                        elif "ETA" in token:
                            eta = tokens[-2]
                            estimated_completion = ""
                            eta_split = eta.split(":")
                            t_u = time_units[-len(eta_split):]
                            for indx, eta_token in enumerate(eta.split(":")):
                                if eta_token == "00":
                                    continue
                                estimated_completion += eta_token + t_u[indx] + " "
                            fields['estimated_completion'] = estimated_completion
                RemoteDataFile().update_transfer(transfer_token, fields)

    thread.close()

