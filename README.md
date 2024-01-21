# tongyi_assistant
基于通义千问的HomeAssistant助手

0.前言
  
    目前暂不支持上下文，测试尝鲜版本日志打印的比较多，勿喷

    问就是后面再弄
  
    智能家居控制部分还有点问题，阿里云的通义千问回复问题有时候有点迷，偶尔不按我的要求来

    关于大模型promot可以自己按需修改，在集成选项里；当前Prompt 模版里默认将三个区域的设备信息吐给大模型('餐厅','书房','客厅')，请自己按需修改，设备越多占用的token越多，注意控制总量，默认上限配置的1000

    对你有帮助的话b站来一波三连，谢谢。
    https://www.bilibili.com/read/cv29878099/

1.HACS添加自定义存储库
HACS-> 右上角三个点-> 自定义存储库
![4806c33b7948dca9715d48901d7f58f](https://github.com/c1pher-cn/tongyi_assistant/assets/13911935/c1aff538-931d-4240-9959-c225beb34384)


存储库：
https://github.com/c1pher-cn/tongyi_assistant

类型：
集成

添加完成后在HACS页面里找到tongyi_assistant 点击下载
![d235bffd4dd7ea93dcb2a1890548eaa](https://github.com/c1pher-cn/tongyi_assistant/assets/13911935/2582c30f-0923-499d-be0f-61a0a568af22)


2.阿里云官网申请开通权限（目前免费）
阿里云上开通DashScope灵积模型服务，并获取api-key https://help.aliyun.com/zh/dashscope/developer-reference/activate-dashscope-and-create-an-api-key


3.配置-集成-添加集成-搜tongyi_assistant-配置-添加api-key

4.配置-语音助手-添加助手

![bef32f3222fcf35046e115bd8b7eeac](https://github.com/c1pher-cn/tongyi_assistant/assets/13911935/dd67f662-66b7-4877-bb90-32eb162dc6cc)


配置对话代理，完成

![ba9cf966fa54ebe73f7112c86790866](https://github.com/c1pher-cn/tongyi_assistant/assets/13911935/b3fe83f7-459d-49e9-b0eb-bf7964a873b4)

选择刚才创建的助手

![925056c75a8768b000f11b946a73029](https://github.com/c1pher-cn/tongyi_assistant/assets/13911935/9f5aef25-845b-4119-88d1-344fffa7f353)

智能家居控制部分还有点问题
