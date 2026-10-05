# Isolated local MySQL instance on this workstation

MySQL Server 8.0 is already installed. This project uses an independent data
directory at `.local/mysql-data` and port **3307**. The existing Windows MySQL80
service on 3306 is untouched. Do not reinitialize this data directory.

Start the existing isolated instance in a terminal from the repository root:

```powershell
& 'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqld.exe' --no-defaults --basedir='C:\Program Files\MySQL\MySQL Server 8.0' --datadir="$PWD\.local\mysql-data" --port=3307 --bind-address=127.0.0.1 --mysqlx=0 --console
```

The localhost root account and project user both have generated passwords in
the ignored `.env`; the application uses only the project user. For an orderly
shutdown from another terminal, run:

```powershell
& 'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqladmin.exe' --host=127.0.0.1 --port=3307 --user=root --password shutdown
```

Enter `MYSQL_LOCAL_ROOT_PASSWORD` privately at the prompt. Never paste it into a
commit or command argument. `scripts/provision_local_mysql.py` is a one-time
bootstrap for a newly initialized local server; it is not a server restart script
and cannot reset an existing root password.
