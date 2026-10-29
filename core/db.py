import os
import clickhouse_connect

def client(admin=False):
    # Only explicitly requested data setup may use the administrator.
    prefix = 'CH_ADMIN' if admin else 'CH_READONLY'
    return clickhouse_connect.get_client(
        host=os.getenv('CH_HOST', '127.0.0.1'), port=int(os.getenv('CH_PORT', '8123')),
        username=os.getenv(prefix + '_USER', 'default' if admin else 'vf_reader'),
        password=os.getenv(prefix + '_PASSWORD', ''),
        database='vf_mock' if not admin else 'default',
        connect_timeout=5, send_receive_timeout=30,
    )
