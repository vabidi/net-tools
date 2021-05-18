
PDIR="/perfDir"


while getopts "ensv" flag; do
  case "${flag}" in
    e) e_flag=true ;;
    n) n_flag=true ;;
    s) s_flag=true ;;
    v) v_flag=true ;;
  esac
done

rm -r $PDIR
mkdir $PDIR

cd /perftools

if [ ! -z ${e_flag} ]; then
    echo 'Collect nic stats'
    nohup ./get_ena_stats.py -d 30 > $PDIR/enastats.out 2>&1 &
fi

if [ ! -z ${n_flag} ]; then
    echo 'Collect net-stats'
    nohup net-stats -A -t WwQqi -i 30 -o  $PDIR/ns.out 2>&1 &
fi

if [ ! -z ${s_flag} ]; then
    echo 'Collect sched stats'
    nohup ./sched_stats.sh  > $PDIR/schedstats.out 2>&1 &
fi

if [ ! -z ${v_flag} ]; then
    echo 'Collect vmkstats'
    nohup ./vmkstats.sh  $PDIR 2>&1 &
fi
