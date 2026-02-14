#!/usr/bin/env python3
"""
UDP Runner Script
Usage: python run_udp.py [server|client] [options]
"""

import sys
import os
import argparse

def main():
    parser = argparse.ArgumentParser(
        description='UDP File Transfer - Server/Client Runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python run_udp.py server
  python run_udp.py server --host 0.0.0.0 --port 6000
  python run_udp.py client --host 192.168.1.100
  python run_udp.py client --port 6001 --folder ./downloads
        ''')

    parser.add_argument('mode', choices=['server', 'client'],
                        help='Run mode: server or client')
    parser.add_argument('--host', type=str, default='127.0.0.1',
                        help='Server IP address (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=6000,
                        help='Server port (default: 6000)')
    parser.add_argument('--folder', type=str, default=None,
                        help='Folder path (server: resource folder, client: download folder)')
    parser.add_argument('--input', type=str, default=None,
                        help='Input file path (client only)')

    args = parser.parse_args()

    if args.mode == "server":
        print("\n" + "="*50)
        print("Starting UDP Server...")
        print("="*50 + "\n")

        # Import and run UDP server
        from server.udp import FileServer

        try:
            HOST = args.host
            PORT = args.port
            dir_path = args.folder if args.folder else input("Enter resource folder path: ")

            print(f"Server Configuration:")
            print(f"  Host: {HOST}")
            print(f"  Port: {PORT}")
            print(f"  Resource Folder: {dir_path}")
            print()

            server = FileServer(HOST, PORT, dir_path)
            server.start_server()
            server.server_socket.close()
            print("\n\033[1;32;40m[NOTIFICATION] Exited the server!\n\033[0m")
        except KeyboardInterrupt:
            print("\n\033[1;32;40m[NOTIFICATION] Server stopped by user.\033[0m")
        except Exception as e:
            print(f"Cannot start Server: {e}")

    elif args.mode == "client":
        print("\n" + "="*50)
        print("Starting UDP Client...")
        print("="*50 + "\n")

        # Import and run UDP client
        from client.udp import FileClient

        try:
            HOST = args.host
            PORT = args.port
            output_path = args.folder if args.folder else input("Enter folder path to save files: ")
            file_input = args.input if args.input else input("Enter input file path: ")

            print(f"Client Configuration:")
            print(f"  Server: {HOST}:{PORT}")
            print(f"  Download Folder: {output_path}")
            print(f"  Input File: {file_input}")
            print()

            client = FileClient(HOST, PORT, output_path, file_input)
            client.start_client()
            client.stop()
            sys.exit(0)
        except KeyboardInterrupt:
            print("\n\033[1;32;40m[NOTIFICATION] Client stopped by user.\033[0m")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
