import clickhouse_connect

if __name__ == '__main__':
    client = clickhouse_connect.get_client(
        host='e9c6hahkgs.ap-south-1.aws.clickhouse.cloud',
        user='default',
        password='StZr2UeOuF7~n',
        secure=True
    )
    print("Result:", client.query("SELECT 1").result_set[0][0])


print("Client:", client)
print("Ping:", client.ping())