#!/bin/bash

function do_test(){
	ORDER=$1
	cd ..
	pwd
	make clean
	make $ORDER
}

function do_serial_test(){
	ORDER=$1
	rm -rf topos-* *.pdf
	
	#for i in $(seq 1 20);
	for i in $(seq 1 2);
	do
		echo
		echo "==============$(date)============="
		echo test $i
	 	
		(do_test $ORDER)
	
		cp -r ../topos topos-$i
		cp -r ../logs  topos-$i/
	
	 	date
		echo sleep 10 seconds
		sleep 10
	 	pwd
	done
	
	python3 plot-all-tests.py
}

#do_serial_test test | tee test.log
#mkdir test-1-2-5-10-20
#mv *.pdf *.log topos-* test-1-2-5-10-20

#sleep 30

#do_serial_test tset | tee test.log
#mkdir test-20-10-5-2-1
#mv *.pdf *.log topos-* test-20-10-5-2-1

do_serial_test tset | tee test.log
mkdir test-ptp4l-1h-20-10-5-2-1
mv *.pdf *.log topos-* test-ptp4l-1h-20-10-5-2-1
