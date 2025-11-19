# 儿童故事生成平台

这是一个基于Flask的儿童故事生成平台后端服务，可以接收用户输入的关键词，调用百度文心一言API生成儿童故事，并支持为故事生成插图和音频。生成的故事、插图和音频会被保存到数据库和本地存储中。

## 功能特点

- 根据用户提供的关键词生成儿童故事
- 将生成的故事保存到SQLite数据库
- 提供RESTful API查询和获取故事
- 自动提取故事标题、梗概和正文
- 为故事生成插图并保存到本地
- 支持通过故事标题或正文片段生成插图
- 为故事生成语音朗读音频并保存到本地
- 提供简单的前端页面用于播放故事音频
- 支持在前端页面中生成音频

## 技术栈

- Python 3.7+
- Flask
- SQLAlchemy (ORM)
- SQLite (数据库)
- 百度文心一言API

## 安装和配置

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置API密钥

在`.env`文件中配置百度文心一言API的密钥：

```
BAIDU_API_KEY=bce-v3/ALTAK-kHoOsiBwcK0XVlweMv3r7/a4426e2c423c1148f75aa1903bcf8fbe7a2e2719
BAIDU_SECRET_KEY=your_baidu_secret_key
FLASK_APP=app.py
FLASK_ENV=development
```

**注意**：你需要到[百度AI开放平台](https://ai.baidu.com/)注册账号并创建应用，获取API Key和Secret Key。

### 3. 数据库结构

应用程序会自动创建以下数据库表：

```sql
CREATE TABLE story (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(200) NOT NULL,
    summary TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME,
    keywords VARCHAR(500),
    illustration_url VARCHAR(500),
    audio_url VARCHAR(500)
);
```

## 使用方法

### 启动服务

```bash
flask run
```

服务默认运行在 `http://localhost:5000`

### API接口

#### 1. 生成故事

**URL**: `/api/generate-story`
**方法**: `POST`
**请求体**: 
```json
{
    "keywords": "宇航员 小狗 月球"
}
```

**响应**: 
```json
{
    "message": "故事生成成功",
    "story": {
        "id": 1,
        "title": "宇航员和小狗的月球冒险",
        "summary": "小明是一名宇航员，他带着他的小狗星星一起登上了月球...",
        "content": "小明是一名宇航员，他带着他的小狗星星一起登上了月球...",
        "created_at": "2023-08-01T12:00:00",
        "keywords": "宇航员 小狗 月球"
    }
}
```

#### 2. 获取所有故事

**URL**: `/api/stories`
**方法**: `GET`
**响应**: 
```json
[
    {
        "id": 1,
        "title": "宇航员和小狗的月球冒险",
        "summary": "小明是一名宇航员，他带着他的小狗星星一起登上了月球...",
        "content": "小明是一名宇航员，他带着他的小狗星星一起登上了月球...",
        "created_at": "2023-08-01T12:00:00",
        "keywords": "宇航员 小狗 月球"
    },
    ...
]
```

#### 3. 获取单个故事

**URL**: `/api/stories/<story_id>`
**方法**: `GET`
**响应**: 
```json
{
    "id": 1,
    "title": "宇航员和小狗的月球冒险",
    "summary": "小明是一名宇航员，他带着他的小狗星星一起登上了月球...",
    "content": "小明是一名宇航员，他带着他的小狗星星一起登上了月球...",
    "created_at": "2023-08-01T12:00:00",
    "keywords": "宇航员 小狗 月球",
    "illustration_url": "/uploads/1a2b3c4d5e6f.png"
}
```

#### 4. 为故事生成插图

**URL**: `/api/stories/<story_id>/generate-illustration`
**方法**: `POST`
**请求体** (可选): 
```json
{
    "text": "宇航员和小狗在月球上玩耍的场景"
}
```

**响应**: 
```json
{
    "message": "插图生成成功",
    "story": {
        "id": 1,
        "title": "宇航员和小狗的月球冒险",
        "summary": "小明是一名宇航员，他带着他的小狗星星一起登上了月球...",
        "content": "小明是一名宇航员，他带着他的小狗星星一起登上了月球...",
        "created_at": "2023-08-01T12:00:00",
        "keywords": "宇航员 小狗 月球",
        "illustration_url": "/uploads/1a2b3c4d5e6f.png"
    }
}
```

#### 5. 访问生成的插图和音频

**URL**: `/uploads/<filename>`
**方法**: `GET`
**说明**: 直接在浏览器中访问该URL可以查看生成的插图图片或播放音频文件。

#### 6. 为故事生成音频

**URL**: `/api/stories/<story_id>/generate-audio`
**方法**: `POST`
**请求体** (可选): 
```json
{
    "text": "小明是一名宇航员，他带着他的小狗星星一起登上了月球..."
}
```

**响应**: 
```json
{
    "message": "音频生成成功",
    "story": {
        "id": 1,
        "title": "宇航员和小狗的月球冒险",
        "summary": "小明是一名宇航员，他带着他的小狗星星一起登上了月球...",
        "content": "小明是一名宇航员，他带着他的小狗星星一起登上了月球...",
        "created_at": "2023-08-01T12:00:00",
        "keywords": "宇航员 小狗 月球",
        "illustration_url": "/uploads/1a2b3c4d5e6f.png",
        "audio_url": "/uploads/7g8h9i0j1k2l.mp3"
    }
}
```

#### 7. 故事播放页面

**URL**: `/play/<story_id>`
**方法**: `GET`
**说明**: 提供一个简单的前端页面，用于展示故事内容并播放音频。如果故事还没有音频，可以在页面上点击按钮生成音频。

## 注意事项

1. 使用前请确保已正确配置百度文心一言、文心一格和语音合成API的密钥
2. 生成的故事、插图和音频质量取决于API返回的结果
3. 图片和音频文件将保存在项目根目录的`uploads`文件夹中
4. 数据库使用SQLite，适合开发和小型应用场景
5. 在生产环境中使用时，建议配置更安全的环境变量管理和API密钥保护措施
6. 如需禁用API功能（用于演示或测试），可以在`app.py`中注释相关API调用代码
7. 语音合成API默认使用女声，语速、语调和音量都设为中等水平，可以在`generate_audio_with_baidu`函数中调整参数

## 许可证

MIT