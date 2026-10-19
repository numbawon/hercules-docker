#!/bin/sh
set -e
# Hercules prints passwords (the inter-server one and players' own) in its login-server log lines; mask them.
sed -i -E '/Show(Notice|Info)\(.*(pass: |received pass)/ { s/sd->passwd/"<hidden>"/g; s/acc\.pass/"<hidden>"/g; s/, pass\);/, "<hidden>");/ }' src/login/login.cpp
! grep -nE 'Show(Notice|Info)\(.*(pass: |received pass)' src/login/login.cpp | grep -E 'passwd|acc\.pass|[ ,]pass[,)]'
