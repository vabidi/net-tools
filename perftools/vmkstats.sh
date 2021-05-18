RDIR="$1/vmkstatsdir"

if [ ! -d $1 ]; then
  echo "ERRROR: Directory $1 does not exist"
  exit 1
fi

mkdir -p $RDIR

echo `uname -a` > ${RDIR}/readme


vsish -e set /perf/vmkstats/command/stop
vsish -e set /perf/vmkstats/command/reset
sleep 2
vsish -e set /perf/vmkstats/command/start
sleep 5
vsish -e set /perf/vmkstats/command/stop
/usr/lib/vmware/vmkstats/bin/vmkstatsdumper -d
/usr/lib/vmware/vmkstats/bin/vmkstatsdumper -a -o ${RDIR}

