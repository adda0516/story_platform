from flask import Flask, request, jsonify, send_from_directory, render_template_string
from flask_sqlalchemy import SQLAlchemy
import requests
import os
import json
import base64
import uuid
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 创建Flask应用
app = Flask(__name__)

# 配置数据库
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///stories.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 创建数据库实例
db = SQLAlchemy(app)

# 确保uploads目录存在
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# 数据库模型
class Story(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    keywords = db.Column(db.String(500))  # 存储用户输入的关键词
    illustration_url = db.Column(db.String(500))  # 存储插图URL或文件路径
    audio_url = db.Column(db.String(500))  # 存储音频URL或文件路径

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'summary': self.summary,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'keywords': self.keywords,
            'illustration_url': self.illustration_url,
            'audio_url': self.audio_url
        }

# 创建数据库表
with app.app_context():
    # 使用alembic-like方式安全地更新表结构
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    # 检查illustration_url字段是否存在
    if 'story' in inspector.get_table_names() and 'illustration_url' not in inspector.get_columns('story'):
        # 添加新字段
        db.engine.execute('ALTER TABLE story ADD COLUMN illustration_url VARCHAR(500)')
    # 检查audio_url字段是否存在
    if 'story' in inspector.get_table_names() and 'audio_url' not in inspector.get_columns('story'):
        # 添加新字段
        db.engine.execute('ALTER TABLE story ADD COLUMN audio_url VARCHAR(500)')
    # 创建所有表（如果不存在）
    db.create_all()

# 获取百度文心一言API的access_token
def get_access_token():
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {
        "grant_type": "client_credentials",
        "client_id": os.getenv("BAIDU_API_KEY"),
        "client_secret": os.getenv("BAIDU_SECRET_KEY")
    }
    response = requests.get(url, params=params)
    result = response.json()
    return result.get("access_token")

# 调用百度文心一格API生成插图
def generate_illustration_with_ERNIE(text):
    access_token = get_access_token()
    url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/text2image/sd_xl?access_token={access_token}"
    
    # 构造提示词，将文本转换为适合图像生成的提示
    prompt = f"为儿童故事创建插图，内容：{text}。风格：卡通、明亮、友好、适合儿童，色彩鲜艳，细节丰富。"
    
    payload = json.dumps({
        "prompt": prompt,
        "negative_prompt": "恐怖、暴力、成人内容、低质量、模糊、变形",
        "width": 1024,
        "height": 1024,
        "steps": 30,
        "guidance_scale": 7.5
    })
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    response = requests.post(url, headers=headers, data=payload)
    result = response.json()
    
    if 'data' in result and 'image' in result['data']:
        return result['data']['image']  # 返回base64编码的图片
    else:
        raise Exception(f"图片生成API调用失败: {result}")

# 保存base64编码的图片到本地
def save_image(base64_image):
    # 生成唯一文件名
    filename = f"{uuid.uuid4().hex}.png"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    
    # 解码并保存图片
    image_data = base64.b64decode(base64_image)
    with open(filepath, 'wb') as f:
        f.write(image_data)
    
    # 返回相对路径
    return f"/uploads/{filename}"

# 调用百度语音合成API生成音频
def generate_audio_with_baidu(text):
    access_token = get_access_token()
    url = f"https://tsn.baidu.com/text2audio?access_token={access_token}"
    
    # 构造请求参数
    params = {
        "tex": text,
        "tok": access_token,
        "cuid": "children_story_platform",
        "ctp": 1,
        "lan": "zh",
        "spd": 5,  # 语速，取值0-9
        "pit": 5,  # 语调，取值0-9
        "vol": 5,  # 音量，取值0-9
        "per": 0   # 发音人，0为女声，1为男声，3为情感合成-度逍遥，4为情感合成-度丫丫
    }
    
    response = requests.get(url, params=params)
    
    # 检查响应是否为音频文件
    if response.headers.get('Content-Type') == 'audio/mp3':
        return response.content
    else:
        raise Exception(f"音频生成API调用失败: {response.text}")

# 保存音频文件到本地
def save_audio(audio_data):
    # 确保uploads目录存在
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    
    # 生成唯一文件名
    filename = f"{uuid.uuid4().hex}.mp3"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    
    # 保存音频文件
    with open(filepath, 'wb') as f:
        f.write(audio_data)
    
    # 返回相对路径
    return f"/uploads/{filename}"

# 调用百度文心一言API生成儿童故事
def generate_story_with_ERNIE(keywords):
    access_token = get_access_token()
    url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions_pro?access_token={access_token}"
    
    # 构造提示词
    prompt = f"请创作一个适合儿童的短故事，包含以下关键词：{keywords}。故事需要有积极的价值观，语言简单易懂，情节生动有趣。"
    
    payload = json.dumps({
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    })
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    response = requests.post(url, headers=headers, data=payload)
    result = response.json()
    
    if 'result' in result:
        return result['result']
    else:
        raise Exception(f"API调用失败: {result}")

# 解析生成的故事，提取标题、梗概和正文
def parse_generated_story(story_text, keywords):
    # 简单的解析逻辑，可以根据实际生成的内容格式调整
    lines = story_text.strip().split('\n')
    
    # 默认标题
    title = f"{keywords}的故事"
    
    # 尝试从第一行提取标题
    if lines and lines[0].strip():
        title = lines[0].strip()
        # 移除标题行末尾可能的标点
        for char in [':', '：', '.', '。']:
            if title.endswith(char):
                title = title[:-1].strip()
        lines = lines[1:]
    
    # 合并剩余行作为正文
    content = '\n'.join([line.strip() for line in lines if line.strip()])
    
    # 生成梗概（取正文前100个字符或第一段）
    paragraphs = content.split('\n')
    summary = paragraphs[0][:100] + '...' if paragraphs else '暂无梗概'
    
    return title, summary, content

# API端点：生成故事
@app.route('/api/generate-story', methods=['POST'])
def generate_story():
    try:
        data = request.json
        keywords = data.get('keywords', '')
        
        if not keywords:
            return jsonify({'error': '关键词不能为空'}), 400
        
        # 调用API生成故事
        generated_text = generate_story_with_ERNIE(keywords)
        
        # 解析生成的故事
        title, summary, content = parse_generated_story(generated_text, keywords)
        
        # 保存到数据库
        story = Story(
            title=title,
            summary=summary,
            content=content,
            keywords=keywords
        )
        
        db.session.add(story)
        db.session.commit()
        
        return jsonify({
            'message': '故事生成成功',
            'story': story.to_dict()
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API端点：获取所有故事
@app.route('/api/stories', methods=['GET'])
def get_stories():
    stories = Story.query.order_by(Story.created_at.desc()).all()
    return jsonify([story.to_dict() for story in stories])

# API端点：根据ID获取单个故事
@app.route('/api/stories/<int:story_id>', methods=['GET'])
def get_story(story_id):
    story = Story.query.get_or_404(story_id)
    return jsonify(story.to_dict())

# API端点：为故事生成插图
@app.route('/api/stories/<int:story_id>/generate-illustration', methods=['POST'])
def generate_illustration_for_story(story_id):
    try:
        # 获取故事
        story = Story.query.get_or_404(story_id)
        
        # 获取请求数据
        data = request.json or {}
        # 优先使用请求中的文本，如果没有则使用故事标题和摘要的组合
        text_for_illustration = data.get('text', f"{story.title}：{story.summary}")
        
        # 调用文心一格API生成插图
        base64_image = generate_illustration_with_ERNIE(text_for_illustration)
        
        # 保存图片到本地
        image_url = save_image(base64_image)
        
        # 更新故事记录
        story.illustration_url = image_url
        db.session.commit()
        
        return jsonify({
            'message': '插图生成成功',
            'story': story.to_dict()
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 静态文件路由，用于访问上传的图片和音频
@app.route('/uploads/<filename>')
def serve_uploads(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# API端点：为故事生成音频
@app.route('/api/stories/<int:story_id>/generate-audio', methods=['POST'])
def generate_audio_for_story(story_id):
    try:
        # 获取故事
        story = Story.query.get_or_404(story_id)
        
        # 获取请求数据
        data = request.json or {}
        # 优先使用请求中的文本，如果没有则使用故事正文
        text_for_audio = data.get('text', story.content)
        
        # 调用百度语音合成API生成音频
        audio_data = generate_audio_with_baidu(text_for_audio)
        
        # 保存音频文件到本地
        audio_url = save_audio(audio_data)
        
        # 更新故事记录
        story.audio_url = audio_url
        db.session.commit()
        
        return jsonify({
            'message': '音频生成成功',
            'story': story.to_dict()
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 简单的前端页面，用于播放故事音频
@app.route('/play/<int:story_id>')
def play_story(story_id):
    story = Story.query.get_or_404(story_id)
    
    # 简单的HTML模板
    html = '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{{ title }} - 故事播放器</title>
        <style>
            body {
                font-family: 'Arial', sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .story-container {
                background-color: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                text-align: center;
            }
            .summary {
                font-style: italic;
                color: #666;
                margin-bottom: 20px;
            }
            .content {
                line-height: 1.6;
                color: #333;
                margin-bottom: 30px;
            }
            .audio-player {
                width: 100%;
                margin-bottom: 20px;
            }
            .illustration {
                max-width: 100%;
                height: auto;
                display: block;
                margin: 20px auto;
                border-radius: 8px;
            }
            .actions {
                display: flex;
                justify-content: center;
                gap: 10px;
                margin-top: 30px;
            }
            button {
                padding: 10px 20px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
            }
            button:hover {
                background-color: #45a049;
            }
            .keyword-tag {
                display: inline-block;
                background-color: #e0e0e0;
                padding: 5px 10px;
                border-radius: 15px;
                margin-right: 5px;
                font-size: 12px;
            }
            .keywords {
                margin-top: 10px;
                margin-bottom: 20px;
            }
        </style>
    </head>
    <body>
        <div class="story-container">
            <h1>{{ title }}</h1>
            <div class="keywords">
                {% for keyword in keywords %}
                    <span class="keyword-tag">{{ keyword }}</span>
                {% endfor %}
            </div>
            <div class="summary">{{ summary }}</div>
            
            {% if illustration_url %}
                <img src="{{ illustration_url }}" alt="故事插图" class="illustration">
            {% endif %}
            
            <div class="content">{{ content }}</div>
            
            {% if audio_url %}
                <h3>音频播放</h3>
                <audio controls class="audio-player">
                    <source src="{{ audio_url }}" type="audio/mpeg">
                    您的浏览器不支持音频播放。
                </audio>
            {% else %}
                <div class="actions">
                    <form id="generate-audio-form">
                        <button type="submit">生成音频</button>
                    </form>
                </div>
            {% endif %}
        </div>
        
        <script>
            // 生成音频的表单提交
            document.getElementById('generate-audio-form')?.addEventListener('submit', async (e) => {
                e.preventDefault();
                const button = e.submitter;
                const originalText = button.textContent;
                button.textContent = '生成中...';
                button.disabled = true;
                
                try {
                    const response = await fetch('/api/stories/{{ story_id }}/generate-audio', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    });
                    
                    const data = await response.json();
                    if (data.message) {
                        alert(data.message);
                        location.reload();
                    } else {
                        alert('生成失败: ' + (data.error || '未知错误'));
                    }
                } catch (error) {
                    alert('请求失败: ' + error.message);
                } finally {
                    button.textContent = originalText;
                    button.disabled = false;
                }
            });
        </script>
    </body>
    </html>
    '''
    
    # 准备模板数据
    keywords = story.keywords.split(' ') if story.keywords else []
    
    # 渲染模板
    return render_template_string(html, 
        story_id=story.id,
        title=story.title,
        summary=story.summary,
        content=story.content,
        keywords=keywords,
        illustration_url=story.illustration_url,
        audio_url=story.audio_url
    )
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True)