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
	for i in $(seq 1 10);
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

function move_result(){
	DIR=$1
	mkdir -p "$DIR"
	mv *.pdf *.log topos-* "$DIR"
}

#do_serial_test test 2>&1 | tee test.log
#move_result test-10m-ptp4l-1-2-5-10-20

do_serial_test test 2>&1 | tee test.log
move_result test-10m-1-2-5-10-20