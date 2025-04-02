from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext,ConversationHandler
import configparser
import logging
import redis
global redis1
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime


now = datetime.now()
print(now)

def main():
    # Load your token and create an Updater for your Bot
    config = configparser.ConfigParser()
    config.read('config.ini')
    updater = Updater(token=(config['TELEGRAM']['ACCESS_TOKEN']), use_context=True)
    dispatcher = updater.dispatcher
    global redis1
    redis1 = redis.Redis(host=(config['REDIS']['HOST']),
                         password=(config['REDIS']['PASSWORD']),
                         port=(config['REDIS']['REDISPORT']),
                         decode_responses=(config['REDIS']['DECODE_RESPONSE']),
                         username=(config['REDIS']['USER_NAME']))

    cred = credentials.Certificate("chriskey.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://chris-5808b-default-rtdb.firebaseio.com'  # 替换为你的URL
    })

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=logging.INFO)

    dispatcher.add_handler(CommandHandler("add", add))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("hello", hello))

    dispatcher.add_handler(CommandHandler("add_event", add_event))
    dispatcher.add_handler(CommandHandler("recommend", recommend_events))
    dispatcher.add_handler(CommandHandler("add_interest", add_interest))
    dispatcher.add_handler(CommandHandler("list_events", list_events))
    dispatcher.add_handler(CommandHandler("list_interests", list_tags_from_events))
    dispatcher.add_handler(CommandHandler("addgroup", add_group))
    dispatcher.add_handler(CommandHandler("group", get_group_by_tag))
    dispatcher.add_handler(CommandHandler("listgroups", list_groups))
    dispatcher.add_handler(CommandHandler('gpt', gpt_command))
    # dispatcher for chatgpt
    global chatgpt
    chatgpt = HKBU_ChatGPT(config)
    #chatgpt_handler = MessageHandler(Filters.text & (~Filters.command),equiped_chatgpt)
    #dispatcher.add_handler(chatgpt_handler)
    # To start the bot:
    updater.start_polling()
    updater.idle()
def echo(update, context):
    reply_message = update.message.text.upper()
    logging.info("Update: " + str(update))
    logging.info("context: " + str(context))
    context.bot.send_message(chat_id=update.effective_chat.id, text= reply_message)
# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def help_command(update: Update, context: CallbackContext) -> None:
    help_text = (
        "可用命令:\n"
        "/add_event - 添加新的活动（标题 | 描述 | 标签 | 日期）\n"
        "/add_interest: 添加兴趣标签（例如：/add_interest VR, AI）\n"
        "/recommend - 推荐根据您的兴趣标签匹配的活动\n"
        "/list_interests - 列出所有的兴趣标签\n"
        "/list_events - 列出所有活动\n"
        "/addgroup:添加讨论组(/addgroup 标签|群链接)\n"
        "/group - 加入讨论组\n"
        "/listgroups - 列出所有兴趣群组\n"
    )
    update.message.reply_text(help_text)
def add(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /add is issued."""
    try:
        global redis1
        logging.info(context.args[0])
        msg = context.args[0] # /add keyword <-- this should store the keyword
        redis1.incr(msg)
        count = redis1.get(msg)
        update.message.reply_text('You have said ' + msg + ' for ' +
                                  count + ' times.')
    except (IndexError, ValueError):
        update.message.reply_text('Usage: /add <keyword>')

def hello(update: Update, context: CallbackContext) -> None:
    """Send a greeting message when the command /hello is issued."""
    try:
        name = context.args[0]  # 获取用户输入的名字
        update.message.reply_text('Good day, {name}!')
    except IndexError:
        update.message.reply_text('Usage: /hello <name>')

def add_event(update: Update, context:CallbackContext) -> None:
    try:
        # 解析参数格式: /add_event 标题 | 描述 | 标签1,标签2 | 日期(YYYY-MM-DD)
        args = " ".join(context.args).split("|")
        if len(args) != 4:
            update.message.reply_text("格式错误！示例：/add_event 比赛 | 描述 | 电竞,王者荣耀 | 2025-04-15")
            return

        title, desc, tags, date = [x.strip() for x in args]
        event_data = {
            "title": title,
            "description": desc,
            "tags": [tag.strip() for tag in tags.split(",")],
            "date": date,
            "creator": f"telegram_{update.effective_user.id}"
        }

        # 写入Firebase
        new_event_ref = db.reference('events').push(event_data)
        update.message.reply_text(f"活动已添加！ID: {new_event_ref.key}")
    except Exception as e:
        update.message.reply_text(f"错误：{str(e)}")


def recommend_events(update: Update, context: CallbackContext) -> None:
    user_id = f"telegram_{update.effective_user.id}"

    # 获取用户兴趣
    user_interests = db.reference(f'users/{user_id}/interests').get() or []
    if not user_interests:
        update.message.reply_text("请先添加兴趣标签！使用命令如：/add_interest VR")
        return

    # 获取所有活动
    all_events = db.reference('events').get() or {}
    recommendations = []

    for event_id, event in all_events.items():
        # 检查日期是否有效（未过期）
        if event.get('date', '') < datetime.now().strftime('%Y-%m-%d'):
            continue

        # 计算兴趣匹配度
        common_tags = set(user_interests) & set(event.get('tags', []))
        if common_tags:
            event['match_score'] = len(common_tags)
            recommendations.append(event)

    # 按匹配度和日期排序
    recommendations.sort(key=lambda x: (-x['match_score'], x['date']))

    # 返回结果
    if not recommendations:
        update.message.reply_text("暂无推荐活动")
    else:
        response = "为您推荐以下活动：\n\n"
        for event in recommendations[:3]:  # 最多3条
            response += f"🎯 {event['title']}\n📅 {event['date']}\n🔖 标签: {', '.join(event['tags'])}\n\n"
        update.message.reply_text(response)


def add_interest(update: Update, context: CallbackContext) -> None:
    if not context.args:
        update.message.reply_text("请指定兴趣标签，例如：/add_interest VR")
        return

    user_id = f"telegram_{update.effective_user.id}"
    interests = [tag.strip() for tag in " ".join(context.args).split(",")]

    # 更新Firebase
    db.reference(f'users/{user_id}/interests').set(interests)
    update.message.reply_text(f"已更新兴趣标签：{', '.join(interests)}")

def list_tags_from_events(update: Update, context: CallbackContext) -> None:
    all_events = db.reference('events').get() or {}
    
    if not all_events:
        update.message.reply_text("当前没有活动，因此也没有标签。")
        return
    
    tags_set = set()
    for event_id, event in all_events.items():
        if 'tags' in event:
            tags_set.update(event['tags'])
    
    if not tags_set:
        update.message.reply_text("活动存在，但未设置任何标签。")
    else:
        update.message.reply_text("所有活动包含的标签：\n- " + "\n- ".join(tags_set))

def list_events(update: Update, context: CallbackContext) -> None:
    all_events = db.reference('events').get() or {}
    if not all_events:
        update.message.reply_text("当前没有活动。")
        return
    
    response = "所有活动列表：\n"
    for event_id, event in all_events.items():
        response += f"\n🎯 {event['title']}\n📅 {event['date']}\n{event['description']}\n"
    
    update.message.reply_text(response)


def add_group(update: Update, context: CallbackContext) -> None:
    try:
        # 解析参数格式: /addgroup "tag"|"link"
        args = " ".join(context.args).split("|")
        if len(args) != 2 or not args[0].strip() or not args[1].strip():
            update.message.reply_text('格式错误！正确格式：/addgroup "标签"|"群链接"\n示例：/addgroup "VR"|"https://t.me/xxx"')
            return

        tag, link = [x.strip().strip('"') for x in args]  # 移除可能的多余引号
        user_id = f"telegram_{update.effective_user.id}"

        # 写入 Firebase
        groups_ref = db.reference('interest_groups')
        new_group_data = {
            "tag": tag,
            "link": link,
            "creator": user_id,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        new_group_ref = groups_ref.push(new_group_data)
        
        update.message.reply_text(
            f"✅ 标签群组已添加！\n"
            f"标签：{tag}\n"
            f"链接：{link}"
        )
    except Exception as e:
        update.message.reply_text(f"❌ 添加失败：{str(e)}")

def get_group_by_tag(update: Update, context: CallbackContext) -> None:
    try:
        if not context.args:
            update.message.reply_text("请指定兴趣标签，例如：/group VR")
            return

        target_tag = " ".join(context.args).strip().upper()  # 统一转为大写匹配
        groups_ref = db.reference('interest_groups')
        all_groups = groups_ref.get() or {}
        
        found_groups = []
        for gid, group in all_groups.items():
            if group.get('tag', '').upper() == target_tag:
                found_groups.append(group)

        if not found_groups:
            update.message.reply_text(f"⚠️ 没有找到与标签 '{target_tag}' 相关的群组")
        else:
            # 优先返回最新添加的群组
            latest_group = max(found_groups, key=lambda x: x['created_at'])
            response = (
                f"🏷️ 标签：{latest_group['tag']}\n"
                f"🔗 群组链接：{latest_group['link']}\n"
                f"🕒 创建时间：{latest_group['created_at']}"
            )
            update.message.reply_text(response)
    except Exception as e:
        update.message.reply_text(f"❌ 查询失败：{str(e)}")

def list_groups(update: Update, context: CallbackContext) -> None:
    try:
        groups_ref = db.reference('interest_groups')
        all_groups = groups_ref.get() or {}
        
        if not all_groups:
            update.message.reply_text("⚠️ 当前没有已注册的兴趣群组")
            return
            
        response = "🏷️ 已注册的兴趣群组列表：\n\n"
        for idx, (gid, group) in enumerate(all_groups.items(), 1):
            response += (
                f"{idx}. [{group.get('tag', '无标签')}]\n"
                f"   🔗 链接：{group.get('link', '无链接')}\n"
                f"   🕒 创建时间：{group.get('created_at', '未知')}\n\n"
            )
        
        update.message.reply_text(response)
    except Exception as e:
        update.message.reply_text(f"❌ 获取群组列表失败：{str(e)}")

def gpt_command(update, context):
    global chatgpt
    if not context.args:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="格式：/gpt 你好"
        )
        return
    user_input = ' '.join(context.args)
    reply_message = chatgpt.submit(user_input)
    logging.info(f"Update: {update}")
    logging.info(f"Context: {context}")
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=reply_message
    )

from ChatGPT_HKBU import HKBU_ChatGPT
def equiped_chatgpt(update, context):
    global chatgpt
    reply_message = chatgpt.submit(update.message.text)
    logging.info("Update: " + str(update))
    logging.info("context: " + str(context))
    context.bot.send_message(chat_id=update.effective_chat.id, text=reply_message)


if __name__ == '__main__':
    main()