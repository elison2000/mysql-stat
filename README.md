## 输出说明
### THREAD INFO  线程信息
```
total 总线程数
active  活动线程数
wait  处于等待的线程数/秒
create 创建的线程数/秒
```

### TRX INFO  事务数据
```
total 正在执行的事务数
wait  正在行锁等待的事务数
MaxSec  正在运行最长的事务的执行时间（秒）
```

### CMD INFO  QPS数据（按语句粒度统计）
```
select  查询次数/秒
insert  插入次数/秒
update  更新次数/秒
delete  删除次数/秒
begin   begin次数/秒
commit  提交次数/秒
rollback 回滚次数/秒
```

### TMP INFO  使用临时表数据
```
mem  创建临时表次数/秒
disk 使用磁盘创建临时表次数/秒
```

### ROWS INFO  QPS数据（按行粒度统计）
```
sort    排序行数/秒，除以CMD INFO的select数，可以知道大概多少比例的语句使用了排序
read    读取行数/秒，除以CMD INFO的select数，可以得到每条sql大概扫描了多少行，比如QPS 100，扫描行数 100000,平均每条sql扫描1000行，是否走了索引，是否存在大sql，结合业务分析是否能优化。
insert  插入行数/秒，除以CMD INFO的insert数,可以判断是否存在大sql，结合commit数，可以分析是否是大事务
update  更新行数/秒，除以CMD INFO的update数,可以判断是否存在大sql，结合commit数，可以分析是否是大事务
delete  删除行数/秒，除以CMD INFO的delete数,可以判断是否存在大sql，结合commit数，可以分析是否是大事务
```
