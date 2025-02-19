import requests
import time
import os
from typing import Dict, Any, Optional, List
from enum import Enum
import json


class PublishStatus(Enum):
    SUCCESS = 0
    PUBLISHING = 1
    ORIGINAL_FAIL = 2
    NORMAL_FAIL = 3
    PLATFORM_AUDIT_FAIL = 4
    USER_DELETE_ALL = 5
    SYSTEM_BAN_ALL = 6


class WeChatAPI:
    BASE_URL = "https://api.weixin.qq.com/cgi-bin"

    def __init__(self, appid: str, secret: str):
        self.appid = appid
        self.secret = secret
        self._access_token = None
        self._expires_at = 0

    def get_access_token(self, force_refresh: bool = False) -> str:
        if force_refresh or time.time() >= self._expires_at:
            self._refresh_access_token()
        return self._access_token

    def _refresh_access_token(self) -> None:
        params = {
            "grant_type": "client_credential",
            "appid": self.appid,
            "secret": self.secret
        }

        response = requests.get(f"{self.BASE_URL}/token", params=params)
        response.raise_for_status()

        result = response.json()
        
        if "errcode" in result:
            raise WeChatAPIError(result["errcode"], result.get("errmsg", "Unknown error"))

        self._access_token = result["access_token"]
        self._expires_at = time.time() + result["expires_in"] - 300  # 提前5分钟刷新

    def upload_media(self, media_type: str, media_path: str) -> Dict[str, Any]:
        """
        上传临时素材
        
        :param media_type: 媒体文件类型，可以为image、voice、video或thumb
        :param media_path: 媒体文件的本地路径
        :return: 包含media_id等信息的字典
        """
        allowed_types = {'image', 'voice', 'video', 'thumb'}
        if media_type not in allowed_types:
            raise ValueError(f"Invalid media type. Must be one of {allowed_types}")

        if not os.path.exists(media_path):
            raise FileNotFoundError(f"File not found: {media_path}")

        url = f"{self.BASE_URL}/media/upload"
        params = {
            "access_token": self.get_access_token(),
            "type": media_type
        }

        with open(media_path, 'rb') as media_file:
            files = {'media': media_file}
            response = requests.post(url, params=params, files=files)

        response.raise_for_status()
        result = response.json()

        if "errcode" in result:
            raise WeChatAPIError(result["errcode"], result.get("errmsg", "Unknown error"))

        return result

    def upload_permanent_material(self, media_type: str, media_path: str, title: Optional[str] = None, introduction: Optional[str] = None) -> Dict[str, Any]:
        """
        上传永久素材
        
        :param media_type: 媒体文件类型，可以为image、voice、video或thumb
        :param media_path: 媒体文件的本地路径
        :param title: 视频素材的标题（仅适用于视频）
        :param introduction: 视频素材的描述（仅适用于视频）
        :return: 包含media_id和url（仅适用于图片）的字典
        """
        allowed_types = {'image', 'voice', 'video', 'thumb'}
        if media_type not in allowed_types:
            raise ValueError(f"Invalid media type. Must be one of {allowed_types}")

        if not os.path.exists(media_path):
            raise FileNotFoundError(f"File not found: {media_path}")

        url = f"{self.BASE_URL}/material/add_material"
        params = {
            "access_token": self.get_access_token(),
            "type": media_type
        }

        with open(media_path, 'rb') as media_file:
            files = {'media': media_file}
            
            if media_type == 'video':
                if not title or not introduction:
                    raise ValueError("Title and introduction are required for video materials.")
                description = json.dumps({
                    "title": title,
                    "introduction": introduction
                }, ensure_ascii=False).encode('utf-8')
                files['description'] = ('description', description, 'application/json')

            response = requests.post(url, params=params, files=files)

        response.raise_for_status()
        result = response.json()

        if "errcode" in result:
            raise WeChatAPIError(result["errcode"], result.get("errmsg", "Unknown error"))

        return result

    def upload_image_for_article(self, image_path: str) -> str:
        """
        上传图文消息内的图片获取URL
        
        :param image_path: 图片文件的本地路径
        :return: 图片的URL
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"File not found: {image_path}")

        url = f"{self.BASE_URL}/media/uploadimg"
        params = {
            "access_token": self.get_access_token()
        }

        with open(image_path, 'rb') as image_file:
            files = {'media': image_file}
            response = requests.post(url, params=params, files=files)

        response.raise_for_status()
        result = response.json()

        if "errcode" in result:
            raise WeChatAPIError(result["errcode"], result.get("errmsg", "Unknown error"))

        return result["url"]

    def add_draft(self, articles: List[Dict[str, Any]]) -> str:
        """
        新增草稿箱图文素材
        
        :param articles: 图文素材列表，每个元素为一篇图文
        :return: 草稿的media_id
        """
        url = f"{self.BASE_URL}/draft/add"
        params = {
            "access_token": self.get_access_token()
        }
        
        data = {
            "articles": articles
        }

        headers = {'Content-Type': 'application/json'}
        json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
        response = requests.post(url, params=params, data=json_data, headers=headers)

        response.raise_for_status()
        result = response.json()

        if "errcode" in result:
            raise WeChatAPIError(result["errcode"], result.get("errmsg", "Unknown error"))

        return result["media_id"]
    
    def publish_draft(self, media_id: str) -> Dict[str, Any]:
        """
        发布草稿箱中的图文素材
        
        :param media_id: 要发布的草稿的media_id
        :return: 包含发布任务ID的字典
        """
        url = f"{self.BASE_URL}/freepublish/submit"
        params = {
            "access_token": self.get_access_token()
        }
        
        data = {
            "media_id": media_id
        }

        response = requests.post(url, params=params, json=data)
        response.raise_for_status()
        result = response.json()

        if result["errcode"] != 0:
            raise WeChatAPIError(result["errcode"], result.get("errmsg", "Unknown error"))

        return {
            "publish_id": result["publish_id"],
            "msg_data_id": result.get("msg_data_id")
        }

    def get_publish_status(self, publish_id: str) -> Dict[str, Any]:
        """
        获取草稿发布状态
        
        :param publish_id: 发布任务ID
        :return: 包含发布状态信息的字典
        """
        url = f"{self.BASE_URL}/freepublish/get"
        params = {
            "access_token": self.get_access_token()
        }
        
        data = {
            "publish_id": publish_id
        }

        response = requests.post(url, params=params, json=data)
        response.raise_for_status()
        result = response.json()

        if "errcode" in result:
            raise WeChatAPIError(result["errcode"], result.get("errmsg", "Unknown error"))

        return self._parse_publish_status(result)

    def _parse_publish_status(self, status_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析发布状态数据
        
        :param status_data: API返回的原始状态数据
        :return: 解析后的状态数据
        """
        status = PublishStatus(status_data["publish_status"])
        result = {
            "publish_id": status_data["publish_id"],
            "status": status,
            "status_description": status.name,
            "fail_idx": status_data.get("fail_idx", [])
        }

        if status == PublishStatus.SUCCESS:
            result["article_id"] = status_data.get("article_id")
            result["article_detail"] = status_data.get("article_detail", {})

        return result
    
        
class WeChatAPIError(Exception):
    def __init__(self, error_code: int, error_message: str):
        self.error_code = error_code
        self.error_message = error_message
        super().__init__(f"WeChat API Error {error_code}: {error_message}")

# 使用示例
if __name__ == "__main__":
    appid = "YOUR_APPID"
    secret = "YOUR_APPSECRET"
    
    wechat_api = WeChatAPI(appid, secret)
    
    try:
        # 获取 access_token
        access_token = wechat_api.get_access_token()
        print("Access Token:", access_token)

        # 上传临时素材
        media_path = "path/to/your/image.jpg"
        result = wechat_api.upload_media("image", media_path)
        print("Upload result:", result)

    except WeChatAPIError as e:
        print(f"WeChat API Error occurred: {e}")
    except requests.RequestException as e:
        print(f"Network error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
