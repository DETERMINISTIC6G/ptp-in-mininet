#!/bin/bash

function do_test(){
	ORDER=$1
	cd ..
	pwd
	make clean
	make $ORDER
}

function do_serial_test(){
	ORDER=$2
	rm -rf topos-* *.pdf
	
	for i in $(seq 1 20);
	do
		date
		echo test $i
	 	
		(do_test $ORDER)
	
		cp -r ../topos topos-$i
	
	 	date
		echo sleep 10 seconds
		sleep 10
	 	pwd
	done
	
	python3 plot-all-tests.py
}

do_serial_test test
mkdir test-1-2-5-10-20
mv *.pdf *.log topos-* test-1-2-5-10-20

do_serial_test tset
mkdir test-20-10-5-2-1
mv *.pdf *.log topos-* test-20-10-5-2-1

