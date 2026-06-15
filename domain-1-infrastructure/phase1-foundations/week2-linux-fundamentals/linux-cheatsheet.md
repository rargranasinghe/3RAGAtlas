# Linux Fundamentals: File Listing, Permissions & File Viewing

A reference guide for navigating files, understanding permission notation,
and reading file contents safely on a Linux system.

---

## 1. Listing Files

### Basic list
```bash
ls
```
Shows files and directories in the current location.

### Detailed list
```bash
ls -l
```
Shows permissions, owner, group, size, modification date, and name.

Example output:
-rw-rw-r-- 1 user user 0 Jun 14 20:59 notes.txt

| Field          | Meaning                   |
|----------------|---------------------------|
| `-rw-rw-r--`   | File type and permissions |
| `1`            | Hard link count            |
| `user`         | Owner                       |
| `user`         | Group                       |
| `0`            | File size (bytes)           |
| `Jun 14 20:59` | Last modified                |
| `notes.txt`    | File name                    |

### Show hidden files
```bash
ls -a
```
Displays all files, including hidden files (those starting with `.`),
e.g. `.bashrc`, `.profile`, `.ssh`, `.gitconfig`. These store shell config,
SSH config, and user preferences — they're normal files, just hidden by default.

### Detailed list including hidden files
```bash
ls -la ~
```
Combines `-l` and `-a` — shows everything in the home directory, including
hidden configuration files.

---

## 2. Permissions

Permissions are displayed as a 10-character string, e.g. `-rw-rw-r--`:
-rw-rw-r--

||| ||| |||

U   G   O

| Section | Meaning      |
|---------|--------------|
| U       | Owner (User) |
| G       | Group        |
| O       | Others       |

### Permission values
| Permission  | Value |
|-------------|-------|
| Read (r)    | 4     |
| Write (w)   | 2     |
| Execute (x) | 1     |

### Common permission numbers
| Octal | Symbolic    |
|-------|-------------|
| 777   | rwxrwxrwx   |
| 755   | rwxr-xr-x   |
| 700   | rwx------   |
| 664   | rw-rw-r--   |
| 644   | rw-r--r--   |
| 600   | rw-------   |
| 444   | r--r--r--   |

### Example: chmod 600
```bash
chmod 600 notes.txt
```
Calculation: `6 = 4+2 = rw-`, `0 = ---`, `0 = ---` → result: `rw-------`
Only the owner can read/write; nobody else has access.

Verify with:
```bash
ls -l notes.txt
```
Expected: `-rw------- 1 user user 0 Jun 14 20:59 notes.txt`

---

## 3. Viewing File Contents

### cat — print entire file
```bash
cat file.txt
```
Good for small files, quick inspection, concatenating files.
Problem: for large files (e.g. a 2,000-line log), output scrolls past instantly.

### less — page through a file
```bash
less file.txt
```
Displays one screen at a time. Lets you scroll, search, and navigate large
files without flooding the terminal.

#### Navigation in less
| Key   | Action            |
|-------|-------------------|
| ↑ / ↓ | Move line by line |
| Space | Next page         |
| b     | Previous page     |
| g     | Beginning of file |
| G     | End of file       |
| /text | Search            |
| n     | Next match        |
| q     | Quit              |

#### Why "less"?
The original pager, `more`, could only move forward through a file. `less`
added backward navigation and search — hence the joke "less is more."

---

## 4. Practical Command Reference

```bash
# View home directory including hidden files
ls -la ~

# Read a small file
cat notes.txt

# Read a large log file
less /var/log/syslog

# Change permissions
chmod 600 notes.txt

# Check permissions
ls -l notes.txt
```

### Permission quick reference
4 = Read    (r)

2 = Write   (w)

1 = Execute (x)
7 = rwx = 4+2+1

6 = rw- = 4+2

5 = r-x = 4+1

4 = r-- = 4

0 = --- = 0
755 = rwxr-xr-x

644 = rw-r--r--

600 = rw-------

700 = rwx------