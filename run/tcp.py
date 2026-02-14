#!/usr/bin/env python3
"""
TCP Runner Script
Usage: python run_tcp.py [server|client] [options]
"""

import sys
import os
import argparse

def main():
    parser = argparse.ArgumentParser(
        description='TCP File Transfer - Server/Client Runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python run_tcp.py server
  python run_tcp.py server --host 0.0.0.0 --port 5000
  python run_tcp.py client --host 192.168.1.100
  python run_tcp.py client --port 5001 --folder ./downloads
        ''')

    parser.add_argument('mode', choices=['server', 'client'],
                        help='Run mode: server or client')
    parser.add_argument('--host', type=str, default='127.0.0.1',
                        help='Server IP address (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=5000,
                        help='Server port (default: 5000)')
    parser.add_argument('--folder', type=str, default=None,
                        help='Folder path (server: resource folder, client: download folder)')
    parser.add_argument('--input', type=str, default=None,
                        help='Input file path (client only)')

    args = parser.parse_args()

    if args.mode == "server":
        print("\n" + "="*50)
        print("Starting TCP Server...")
        print("="*50 + "\n")

        # Import and run TCP server
        from server.tcp import Server

        try:
            HOST = args.host
            PORT = args.port
            folder_path = args.folder if args.folder else input("Enter resource folder path: ")

            print(f"Server Configuration:")
            print(f"  Host: {HOST}")
            print(f"  Port: {PORT}")
            print(f"  Resource Folder: {folder_path}")
            print()

            Server(HOST, PORT, folder_path)
        except KeyboardInterrupt:
            print("\n\033[1;32;40m[NOTIFICATION] Server stopped by user.\033[0m")
        except Exception as e:
            print(f"Cannot start Server: {e}")

    elif args.mode == "client":
        print("\n" + "="*50)
        print("Starting TCP Client...")
        print("="*50 + "\n")

        # Import and run TCP client
        from client.tcp import Client

        try:
            HOST = args.host
            PORT = args.port
            folder_path = args.folder if args.folder else input("Enter folder path to save files: ")
            input_path = args.input if args.input else input("Enter input file path: ")

            print(f"Client Configuration:")
            print(f"  Server: {HOST}:{PORT}")
            print(f"  Download Folder: {folder_path}")
            print(f"  Input File: {input_path}")
            print()

            Client(HOST, PORT, folder_path, input_path)
        except KeyboardInterrupt:
            print("\n\033[1;32;40m[NOTIFICATION] Client stopped by user.\033[0m")
        except Exception as e:
            print(f"Cannot connect to Server: {e}")

if __name__ == "__main__":
    main()
