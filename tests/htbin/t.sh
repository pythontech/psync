#!/bin/sh
echo "Status: 403"
echo "Content-type: text/plain"
echo "X-pt: abc"
echo "X-pt: def,"
echo "      ghi"
echo
echo "Hello world"
id
