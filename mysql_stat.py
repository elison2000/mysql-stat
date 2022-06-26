#!/usr/bin/python3
# !/usr/bin/python3
# -*- encoding: utf-8 -*-
####################################################################################################
#  Name        :  mysql_stat.py
#  Author      :  Elison
#  Date        :  2021-06-16
#  Description :  监控mysql各项性能指标
#  Updates     :
#      Version     When            What
#      --------    -----------     -----------------------------------------------------------------
#      v1.0        2021-06-16      确定原型
#      v1.0.1      2021-07-23      文件写入方式改为写入后关闭句柄，方便清理日志
#      v1.0.2      2022-06-03      修复bug
####################################################################################################

import sys
import time
import pymysql
import argparse


def get_args():
    '获取参数'
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--version", action='store_true', help="查看版本")
    parser.add_argument("-H", "--host", type=str, help="实例IP和端口, 如: 10.0.0.201:3306")
    parser.add_argument("-u", "--user", type=str, default='dba_ro', help="登录用户")
    parser.add_argument("-p", "--password", type=str, default='abc123', help="登录密码")
    parser.add_argument("-i", "--interval", type=int, default=5, help="查询指标数据的间隔时间（秒）")
    parser.add_argument("-o", "--output", action='store_true', help="输出到日志文件")

    args = parser.parse_args()

    # 处理参数
    if args.version:
        print(__doc__)
        sys.exit()

    try:
        host, port = args.host.split(':')
        host.split('.')[3]
        port = int(port)
        args.host = host
        args.port = port
    except Exception as e:
        print("无效参数：-H")
        print("Usage: ./mysql_stat.py -H 10.0.0.201:3306")
        sys.exit()

    if args.output:
        args.filename = "{0}_{1}_mysql_stat.log".format(args.host, args.port)
    else:
        args.filename = None

    return args


def get_now():
    "获取当前时间"
    now = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    return now


class mysql:
    def __init__(self, conf):
        "创建数据库连接"
        conf['charset'] = 'utf8mb4'
        conf['cursorclass'] = pymysql.cursors.DictCursor
        self.conn = pymysql.connect(**conf)

    def query(self, sql):
        "查询"
        cur = self.conn.cursor()
        cur.execute(sql)
        res = cur.fetchall()
        cur.close()
        return res

    def close(self):
        "关闭连接"
        self.conn.close()


def format_data(data):
    global fieldname_list, field_len_list
    text = "|"
    for i in range(len(fieldname_list)):
        text = text + str(data.get(fieldname_list[i])).rjust(field_len_list[i], ' ') + "|"
    return text


def output(text, filename=None):
    "输出文本"
    if filename:
        f = open(filename, 'a')
        f.write(text + "\n")
        f.close()
    else:
        print(text)


def get_status(db):
    stats = {}
    stats['time'] = get_now()

    # thread info
    sql = """select count(*) totalThreads,sum(case when  command<>'Sleep' and user<> 'system user' then 1 else 0 end) activeThreads,sum(case when  state like 'Waiting for %' and user not in ('system user','event_scheduler') then 1 else 0 end) waitingThreads  from information_schema.processlist"""
    result = db.query(sql)[0]
    stats['totalThreads'] = result['totalThreads']
    stats['activeThreads'] = result['activeThreads']
    stats['waitingThreads'] = result['waitingThreads']

    # trx info
    sql = """select count(*) totalTrx, ifnull(sum(case when  trx_state='LOCK WAIT' then 1 else 0 end),0) waitingTrx,ifnull(max(timestampdiff(second, trx_started, now())),0) trxMaxSec   from information_schema.innodb_trx"""
    result = db.query(sql)[0]
    stats['totalTrx'] = result['totalTrx']
    stats['waitingTrx'] = result['waitingTrx']
    stats['trxMaxSec'] = result['trxMaxSec']

    # slave info
    sql = """show slave status"""
    result = db.query(sql)
    if result:
        lag_sec = result[0]['Seconds_Behind_Master']
        if lag_sec is None:
            lag_sec = 99999
    else:
        lag_sec = 0
    stats['slaveLag'] = lag_sec

    # 批量获取状态值
    sql = "show global status where variable_name in ('Connections','Com_begin', 'Innodb_buffer_pool_pages_dirty', 'Innodb_buffer_pool_pages_flushed', 'Innodb_buffer_pool_pages_free', 'Innodb_buffer_pool_reads', 'Innodb_buffer_pool_read_requests', 'Innodb_buffer_pool_write_requests', 'Com_commit', 'Created_tmp_tables', 'Created_tmp_disk_tables', 'Com_delete', 'Innodb_rows_deleted', 'Com_insert', 'Innodb_rows_inserted', 'Innodb_rows_read', 'Bytes_received', 'Com_rollback', 'Com_select', 'Bytes_sent', 'Sort_rows', 'Com_update', 'Innodb_rows_updated')"

    t1 = time.time()
    res0 = db.query(sql)
    time.sleep(1)
    res1 = db.query(sql)
    t2 = time.time()

    d0 = {}
    d1 = {}

    for i in res0:
        try:
            key = i['Variable_name']
            val = i['Value']
            d0[key] = int(val)
        except Exception:
            pass

    for i in res1:
        try:
            key = i['Variable_name']
            val = i['Value']
            d1[key] = int(val)
        except Exception:
            pass

    # thread create
    stats['createThreads'] = d1['Connections'] - d0['Connections']
    # DB_sentMB,DB_receivedMB
    stats['sentMB'] = round((d1['Bytes_sent'] - d0['Bytes_sent']) / 1024 / 1024)
    stats['receivedMB'] = round((d1['Bytes_received'] - d0['Bytes_received']) / 1024 / 1024)

    # DB_sortRow,DB_readRow,DB_insertRow,DB_updateRow,DB_deleteRow
    stats['sortRows'] = d1['Sort_rows'] - d0['Sort_rows']
    stats['readRows'] = d1['Innodb_rows_read'] - d0['Innodb_rows_read']
    stats['insertRows'] = d1['Innodb_rows_inserted'] - d0['Innodb_rows_inserted']
    stats['updateRows'] = d1['Innodb_rows_updated'] - d0['Innodb_rows_updated']
    stats['deleteRows'] = d1['Innodb_rows_deleted'] - d0['Innodb_rows_deleted']

    # DB_select,DB_insert,DB_update,DB_delete,DB_begin,DB_commit,DB_rollback
    stats['select'] = d1['Com_select'] - d0['Com_select']
    stats['insert'] = d1['Com_insert'] - d0['Com_insert']
    stats['update'] = d1['Com_update'] - d0['Com_update']
    stats['delete'] = d1['Com_delete'] - d0['Com_delete']
    stats['begin'] = d1['Com_begin'] - d0['Com_begin']
    stats['commit'] = d1['Com_commit'] - d0['Com_commit']
    stats['rollback'] = d1['Com_rollback'] - d0['Com_rollback']

    # DB_createTmp,DB_createTmpDisk
    stats['createTmp'] = d1['Created_tmp_tables'] - d0['Created_tmp_tables']
    stats['createTmpDisk'] = d1['Created_tmp_disk_tables'] - d0['Created_tmp_disk_tables']

    # DB_BPReadMB,DB_BPPhyReadMB,DB_BPWriteMB,DB_BPDirtyMB,DB_BPFlushMB,DB_BPFreeMB
    stats['BPReadMB'] = round(
        (d1['Innodb_buffer_pool_read_requests'] - d0['Innodb_buffer_pool_read_requests']) * 16 / 1024)
    stats['BPPhyReadMB'] = round((d1['Innodb_buffer_pool_reads'] - d0['Innodb_buffer_pool_reads']) * 16 / 1024)
    stats['BPWriteMB'] = round(
        (d1['Innodb_buffer_pool_write_requests'] - d0['Innodb_buffer_pool_write_requests']) * 16 / 1024)
    stats['BPDirtyMB'] = round(
        (d1['Innodb_buffer_pool_pages_dirty'] - d0['Innodb_buffer_pool_pages_dirty']) * 16 / 1024)
    stats['BPFlushMB'] = round(
        (d1['Innodb_buffer_pool_pages_flushed'] - d0['Innodb_buffer_pool_pages_flushed']) * 16 / 1024)
    stats['BPFreeMB'] = round((d1['Innodb_buffer_pool_pages_free'] - d0['Innodb_buffer_pool_pages_free']) * 16 / 1024)

    return stats


# main
args = get_args()
sleep_time = args.interval
conf = {'host': args.host, 'port': args.port, 'user': args.user, 'password': args.password}

# 定义打印列
fieldname_list = ['time', 'totalThreads', 'activeThreads', 'waitingThreads', 'createThreads', 'totalTrx', 'waitingTrx',
                  'trxMaxSec',
                  'select',
                  'insert', 'update', 'delete', 'begin', 'commit', 'rollback', 'createTmp', 'createTmpDisk',
                  'sortRows', 'readRows', 'insertRows', 'updateRows', 'deleteRows', 'sentMB', 'receivedMB']
# 定义打印宽度
field_len_list = [19, 9, 6, 6, 6, 6, 6, 8, 8, 8, 8, 8, 8, 8, 8, 6, 6, 10, 10, 10, 10, 10, 8, 8]
head1 = "|                   |--------- THREAD INFO --------|------ TRX INFO ------|-------------------------- CMD INFO --------------------------|-- TMP INFO -|----------------------- ROWS INFO --------------------|- NETWORK INFO --|"
head2 = "|        time       |    total|active|  wait|create| total|  wait|  MaxSec|  select|  insert|  update|  delete|   begin|  commit|rollback|   mem|  disk|      sort|      read|    insert|    update|    delete|   outMB|    inMB|"

while True:
    db = mysql(conf)
    output(head1, args.filename)
    output(head2, args.filename)
    for i in range(20):
        stats = get_status(db)
        text = format_data(stats)
        output(text, args.filename)
        time.sleep(sleep_time - 1)
    db.close()
