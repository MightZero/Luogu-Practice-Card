import json
import os
import math
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import svgwrite
from PIL import ImageFont
import asyncio
from playwright.async_api import async_playwright

# 设置缓存文件路径
cache_file = 'difficulty_cache.json'
uid = 542063  # 设定用户的 UID


# 检查缓存文件是否存在以及是否过期
def is_cache_valid():
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as file:
            cache_data = json.load(file)
            timestamp = datetime.strptime(cache_data['timestamp'], '%Y-%m-%d %H:%M:%S')
            # 检查缓存是否过期及 UID 是否一致
            if datetime.now() - timestamp < timedelta(hours=1) and cache_data.get('uid') == uid:
                return True, cache_data.get('username', 'None')
    return False, 'None'


# 从缓存文件中读取数据
def read_cache():
    with open(cache_file, 'r') as file:
        cache_data = json.load(file)
        return cache_data['difficulty_counts'], cache_data['difficulty_colors'], cache_data.get('username', 'None')


# 将数据写入缓存文件
def write_cache(difficulty_counts, difficulty_colors, username):
    cache_data = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'difficulty_counts': difficulty_counts,
        'difficulty_colors': difficulty_colors,
        'username': username,
        'uid': uid  # 存储当前 UID
    }
    with open(cache_file, 'w') as file:
        json.dump(cache_data, file)


# 异步获取页面内容
async def fetch_page_content():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # 无头浏览器
        page = await browser.new_page()

        # 设置用户的洛谷个人主页 URL
        url = f'https://www.luogu.com/user/{uid}#practice'

        # 打开页面
        await page.goto(url)

        # 等待页面加载
        await page.wait_for_selector('div.difficulty-tags')

        # 获取页面的 HTML
        page_content = await page.content()
        await browser.close()

        return page_content


# 如果缓存有效，则使用缓存数据，否则从网页获取数据
cache_valid, username = is_cache_valid()
if cache_valid:
    difficulty_counts, difficulty_colors, username = read_cache()
else:
    # 异步运行 Playwright 获取页面内容
    page_content = asyncio.run(fetch_page_content())

    # 使用 BeautifulSoup 解析页面内容
    soup = BeautifulSoup(page_content, 'html.parser')

    # 查找不同种类题目的数量和颜色
    difficulty_stats = soup.find('div', class_='difficulty-tags')
    difficulty_counts = {}
    difficulty_colors = {}

    for row in difficulty_stats.find_all('div', class_='row'):
        difficulty_name = row.find('span', class_='lfe-caption').text.strip().replace('\u2212', '-')
        problem_count = int(row.find('span', class_='problem-count').text.strip().replace('题', ''))
        style = row.find('span', class_='lfe-caption')['style']
        color = style.split('background:')[1].strip().split(';')[0]
        if color.startswith('rgb'):
            color = color.replace('rgb', '').replace('(', '').replace(')', '').replace(' ', '').split(',')
            color = '#%02x%02x%02x' % (int(color[0]), int(color[1]), int(color[2]))
        difficulty_counts[difficulty_name] = problem_count
        difficulty_colors[difficulty_name] = color

    # 获取网页标题中的用户名
    title_tag = soup.find('title')
    if title_tag:
        title_text = title_tag.text
        if '的个人中心' in title_text:
            username = title_text.split('的个人中心')[0]
        else:
            username = 'None'
    else:
        username = 'None'

    # 将数据写入缓存文件
    write_cache(difficulty_counts, difficulty_colors, username)

# 翻转数据和标签
difficulty_names = list(difficulty_counts.keys())
problem_counts = list(difficulty_counts.values())
colors = [difficulty_colors[name] for name in difficulty_names]

# 计算上界
max_count = max(problem_counts)
upper_limit = math.ceil(max_count / 50) * 50

# 计算最大文本宽度
def calculate_text_width(text, font_family='SimHei', font_size=12):
    try:
        # 加载字体
        font = ImageFont.truetype(font_family + '.ttf', font_size)
    except IOError:
        # 如果字体文件不存在，使用默认字体
        font = ImageFont.load_default()

    # 计算文本边界框
    bbox = font.getbbox(text)
    text_width = bbox[2] - bbox[0]
    return text_width

max_text_width = 0
for name in difficulty_names:
    text_width = calculate_text_width(name)
    if text_width > max_text_width:
        max_text_width = text_width

for count in problem_counts:
    text_width = calculate_text_width(f'{count} 题')
    if text_width > max_text_width:
        max_text_width = text_width

# 计算柱形图的总宽度
bar_width = 40
bar_height = 400 / len(difficulty_names)
total_bar_width = 600  # 柱形图的总宽度
total_text_width = max_text_width + 10  # 题目难度文字的宽度加上一些间距
total_width = total_bar_width + total_text_width + 20  # 柱形图宽度 + 文字宽度 + 间距

# 计算卡片宽度和高度
card_width = total_width + 100  # 卡片宽度
card_height = 600  # 卡片高度，确保有足够的空间

# 创建 SVG 文件
dwg = svgwrite.Drawing('difficulty_counts.svg', profile='tiny', size=(card_width, card_height))

# 设置卡片样式
card = dwg.rect(insert=(50, 50), size=(card_width - 100, card_height - 100), rx=10, ry=10, fill='white', stroke='lightgray', stroke_width=1)
dwg.add(card)

# 添加标题文字
title_text = f'{username}的练习情况'
title_font_size = 24
title_text_width = calculate_text_width(title_text, font_size=title_font_size)
title_text_x = 100  # 距离左侧50 + 10间距
title_text_y = 100  # 距离顶部50 + 30间距
title = dwg.text(title_text, insert=(title_text_x, title_text_y), font_family='SimHei', font_size=title_font_size, text_anchor='start')
dwg.add(title)

# 计算柱形图的位置和大小
x_offset = 50 + total_text_width + 50  # 居中柱形图
y_offset = 120  # 距离顶部50 + 70间距

# 计算缩放比例
max_bar_width = total_bar_width
if(max_count!=0):
    scale_factor = 0.8 * max_bar_width / max_count
else:
    scale_factor = 0.8 * max_bar_width / 1

# 绘制柱形图并添加题目难度标签
for i, (name, count, color) in enumerate(zip(difficulty_names, problem_counts, colors)):
    bar_x = x_offset
    bar_y = y_offset + i * bar_height

    # 计算柱形宽度并应用缩放比例
    bar_width_scaled = count * scale_factor

    # 绘制柱形
    bar = dwg.rect(insert=(bar_x, bar_y), size=(bar_width_scaled, bar_height - 5), rx=5, ry=5, fill=color,
                   stroke='lightgray', stroke_width=1)
    dwg.add(bar)

    # 添加题目数量标签
    text_count = dwg.text(f'{count} 题', insert=(bar_x + bar_width_scaled + 10, bar_y + bar_height / 2),
                          font_family='SimHei', font_size=12, text_anchor='start')
    dwg.add(text_count)

    # 添加题目难度标签
    text_difficulty = dwg.text(name, insert=(bar_x - 10, bar_y + bar_height / 2),  # 紧贴柱形图左边
                               font_family='SimHei', font_size=12, text_anchor='end')
    dwg.add(text_difficulty)

# 保存 SVG 文件
dwg.save()

# 输出 SVG 文件路径
print('SVG 文件已保存为 difficulty_counts.svg')
