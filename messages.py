MESSAGES = {
    "status": {
        "op": "status",
        "fields": {
            "display_status": "已连接",
            "startup_check": {
                "title": "启动检查",
                "steps": [
                    {
                        "key": "plugin",
                        "title": "启动插件",
                        "state": "ok",
                        "detail": "插件进程已连接 DGHub",
                    },
                    {
                        "key": "source",
                        "title": "外部数据源",
                        "state": "pending",
                        "detail": "等待外部程序连接",
                        "hint": "确认外部程序已启动，并允许本插件读取数据"
                    }
                ],
            },
        },
    },
}