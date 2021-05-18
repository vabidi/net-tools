esxcfg-advcfg -s 5120 /Net/NetSchedHClkLeafQueueDepthPktMAX
vsish -e set /net/pNics/vmnic0/sched/useResPoolsCfg 0
vsish -e set /net/pNics/vmnic0/sched/allowResPoolsSched 0
vsish -e set /net/pNics/vmnic0/sched/useResPoolsCfg 1
vsish -e set /net/pNics/vmnic0/sched/allowResPoolsSched 1
vsish -e get /config/Net/intOpts/NetSchedHClkLeafQueueDepthPktMAX
