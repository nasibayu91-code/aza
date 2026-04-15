import asyncio
import aiohttp
import json
import re
import os
import base64
from datetime import datetime
from typing import Optional, Dict, List
import logging

logging.basicConfig(level=logging.INFO)

class FreeGodEye:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Бесплатные эндпоинты LLM
        self.llm_endpoints = {
            "deepseek": {
                "url": "https://api.deepseek.com/v1/chat/completions",
                "key": os.getenv("DEEPSEEK_API_KEY", ""),  # Бесплатно при регистрации
                "model": "deepseek-chat"
            },
            "groq": {
                "url": "https://api.groq.com/openai/v1/chat/completions",
                "key": os.getenv("GROQ_API_KEY", ""),  # Бесплатно при регистрации
                "model": "llama-3.3-70b-versatile"
            },
            "huggingface": {
                "url": "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-72B-Instruct",
                "key": os.getenv("HF_API_KEY", ""),  # Бесплатно
                "model": "qwen"
            }
        }
        
        # Бесплатный эндпоинт для Flux (генерация картинок)
        self.image_endpoints = {
            "flux": "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell",
            "sd": "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-3.5-large"
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    # ========== 1. ПОИСК ПО НИКУ (50+ САЙТОВ) ==========
    async def search_username_global(self, username: str) -> Dict:
        """Бесплатный поиск по 50+ платформам через What's My Name API"""
        url = f"https://whatsmyname.app/api/v1/username?username={username}"
        
        try:
            async with self.session.get(url, timeout=30) as resp:
                data = await resp.json()
                
                results = {
                    "found": [],
                    "total_checked": 0,
                    "report": ""
                }
                
                for site in data.get("sites", []):
                    results["total_checked"] += 1
                    if site.get("status") == "claimed":
                        results["found"].append({
                            "platform": site.get("name"),
                            "url": site.get("uri_check").replace("{username}", username),
                            "category": site.get("cat")
                        })
                
                results["report"] = f"Найдено {len(results['found'])} профилей из {results['total_checked']} проверенных"
                return results
                
        except Exception as e:
            return {"error": str(e), "found": []}
    
    # ========== 2. ПОИСК УТЕЧЕК (БЕСПЛАТНО) ==========
    async def check_breaches_free(self, query: str, query_type: str = "email") -> Dict:
        """
        Бесплатная проверка через публичные API
        Поддерживает: email, username, phone, ip
        """
        results = {
            "sources": [],
            "total_breaches": 0,
            "passwords_found": [],
            "details": []
        }
        
        # 1. Проверка через Firefox Monitor (публичный API)
        if query_type == "email":
            # Используем публичный эндпоинт Firefox Monitor
            url = f"https://monitor.firefox.com/api/v1/scan"
            data = {"email": query}
            
            try:
                async with self.session.post(url, json=data, timeout=15) as resp:
                    if resp.status == 200:
                        breaches = await resp.json()
                        for breach in breaches.get("breaches", []):
                            results["sources"].append(breach.get("Name"))
                            results["details"].append({
                                "name": breach.get("Title"),
                                "date": breach.get("BreachDate"),
                                "data_classes": breach.get("DataClasses", [])
                            })
                        results["total_breaches"] = len(results["sources"])
            except:
                pass
        
        # 2. Поиск в публичных пастбинах через Psbdmp
        url = f"https://psbdmp.cc/api/v3/search/{query}"
        try:
            async with self.session.get(url, timeout=10) as resp:
                data = await resp.json()
                for paste in data.get("data", [])[:5]:
                    results["details"].append({
                        "type": "paste",
                        "id": paste.get("id"),
                        "date": paste.get("date"),
                        "title": paste.get("title", "Без названия")
                    })
        except:
            pass
        
        # 3. Поиск в утечках через Snusbase (публичный)
        url = f"https://snusbase.com/api/public/search"
        data = {"terms": [query], "types": [query_type], "limit": 10}
        
        try:
            async with self.session.post(url, json=data, timeout=15) as resp:
                result = await resp.json()
                if result.get("results"):
                    for db, entries in result["results"].items():
                        results["sources"].append(db)
                        for entry in entries:
                            if "password" in entry:
                                results["passwords_found"].append(entry["password"][:3] + "***")
        except:
            pass
        
        return results
    
    # ========== 3. ОПРЕДЕЛЕНИЕ ТЕЛЕФОНА ==========
    async def analyze_phone(self, phone: str) -> Dict:
        """Бесплатный анализ номера через открытые API"""
        clean = re.sub(r'[^\d]', '', phone)
        
        # База кодов РФ (расширенная)
        operators_db = {
            "900": "МТС", "901": "МТС", "902": "Билайн", "903": "Билайн",
            "904": "МегаФон", "905": "МегаФон", "906": "Билайн", "907": "МТС",
            "908": "МТС", "909": "Билайн", "910": "МТС", "911": "МТС",
            "912": "МегаФон", "913": "МТС", "914": "Билайн", "915": "МТС",
            "916": "МТС", "917": "МТС", "918": "МТС", "919": "МТС",
            "920": "МегаФон", "921": "МегаФон", "922": "МегаФон", "923": "МегаФон",
            "924": "МегаФон", "925": "МегаФон", "926": "МегаФон", "927": "МегаФон",
            "928": "МегаФон", "929": "МегаФон", "930": "МегаФон", "931": "МегаФон",
            "932": "МегаФон", "933": "МегаФон", "934": "МегаФон", "935": "МегаФон",
            "936": "МегаФон", "937": "МегаФон", "938": "МегаФон", "939": "МегаФон",
            "950": "Tele2", "951": "Tele2", "952": "Tele2", "953": "Tele2",
            "960": "Билайн", "961": "Билайн", "962": "Билайн", "963": "Билайн",
            "964": "Билайн", "965": "Билайн", "966": "Билайн", "967": "Билайн",
            "968": "Билайн", "980": "МТС", "981": "МТС", "982": "МТС", "983": "МТС",
            "984": "МТС", "985": "МТС", "986": "МТС", "987": "МТС", "988": "МТС",
            "989": "МТС", "999": "Прочие"
        }
        
        # Регионы по кодам
        regions_db = {
            "495": "Москва", "499": "Москва", "812": "Санкт-Петербург",
            "383": "Новосибирск", "343": "Екатеринбург", "846": "Самара",
            "861": "Краснодар", "863": "Ростов-на-Дону", "831": "Нижний Новгород",
            "351": "Челябинск", "384": "Кемерово", "391": "Красноярск"
        }
        
        prefix = clean[1:4] if clean.startswith(('7', '8')) else clean[:3]
        operator = operators_db.get(prefix, "Неизвестный")
        
        region_code = clean[1:4] if clean.startswith('7') else clean[:3]
        region = regions_db.get(region_code, "Не определён")
        
        # Бесплатное API для проверки номера
        validation = {}
        try:
            url = f"https://htmlweb.ru/geo/api.php?json&telcod={clean}"
            async with self.session.get(url, timeout=10) as resp:
                data = await resp.json()
                validation = {
                    "country": data.get("country", {}).get("name", "Неизвестно"),
                    "region": data.get("region", {}).get("name", "Неизвестно"),
                    "operator": data.get("0", {}).get("oper", "Неизвестно")
                }
        except:
            pass
        
        return {
            "phone": clean,
            "operator": validation.get("operator") or operator,
            "region": validation.get("region") or region,
            "country": validation.get("country", "Россия"),
            "formatted": f"+7 ({clean[1:4]}) {clean[4:7]}-{clean[7:9]}-{clean[9:11]}"
        }
    
    # ========== 4. ПОИСК ПО EMAIL (БЕСПЛАТНО) ==========
    async def search_email(self, email: str) -> Dict:
        """Поиск всей доступной информации по email"""
        results = {
            "valid": False,
            "provider": None,
            "gravatar": None,
            "breaches": None,
            "social": []
        }
        
        # Проверка валидности через бесплатное API
        try:
            url = f"https://api.mailcheck.ai/email/{email}"
            async with self.session.get(url, timeout=10) as resp:
                data = await resp.json()
                results["valid"] = data.get("disposable", False) == False
                results["provider"] = data.get("mx", True)
        except:
            pass
        
        # Gravatar
        import hashlib
        email_hash = hashlib.md5(email.lower().encode()).hexdigest()
        results["gravatar"] = f"https://www.gravatar.com/avatar/{email_hash}?d=404&s=200"
        
        # Поиск соцсетей по email через Holehe
        try:
            # Используем публичный API holehe
            url = f"https://holehe.deno.dev/?email={email}"
            async with self.session.get(url, timeout=20) as resp:
                data = await resp.json()
                for site, exists in data.items():
                    if exists:
                        results["social"].append(site)
        except:
            pass
        
        # Проверка утечек
        results["breaches"] = await self.check_breaches_free(email, "email")
        
        return results
    
    # ========== 5. ПОИСК ПО IP ==========
    async def analyze_ip(self, ip: str) -> Dict:
        """Бесплатный анализ IP через ip-api.com"""
        url = f"http://ip-api.com/json/{ip}?fields=66846719"
        
        try:
            async with self.session.get(url, timeout=10) as resp:
                data = await resp.json()
                
                if data.get("status") == "success":
                    return {
                        "ip": data.get("query"),
                        "country": data.get("country"),
                        "region": data.get("regionName"),
                        "city": data.get("city"),
                        "isp": data.get("isp"),
                        "org": data.get("org"),
                        "as": data.get("as"),
                        "lat": data.get("lat"),
                        "lon": data.get("lon"),
                        "timezone": data.get("timezone"),
                        "vpn_proxy": data.get("proxy"),
                        "hosting": data.get("hosting"),
                        "mobile": data.get("mobile"),
                        "maps_url": f"https://www.google.com/maps?q={data.get('lat')},{data.get('lon')}"
                    }
        except Exception as e:
            return {"error": str(e)}
    
    # ========== 6. БЕСПЛАТНЫЙ ИИ-ЧАТ ==========
    async def ask_ai(self, prompt: str, provider: str = "deepseek") -> str:
        """Бесплатный запрос к нейросети"""
        
        if provider == "deepseek":
            url = "https://api.deepseek.com/chat/completions"
            headers = {
                "Authorization": f"Bearer {os.getenv('DEEPSEEK_API_KEY')}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2000
            }
        
        elif provider == "groq":
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2000
            }
        
        else:  # huggingface
            url = "https://api-inference.huggingface.co/models/mistralai/Mixtral-8x7B-Instruct-v0.1"
            headers = {
                "Authorization": f"Bearer {os.getenv('HF_API_KEY')}",
                "Content-Type": "application/json"
            }
            data = {
                "inputs": f"<s>[INST] {prompt} [/INST]",
                "parameters": {"max_new_tokens": 2000}
            }
        
        try:
            async with self.session.post(url, headers=headers, json=data, timeout=60) as resp:
                result = await resp.json()
                
                if provider == "huggingface":
                    return result[0]["generated_text"].split("[/INST]")[-1].strip()
                else:
                    return result["choices"][0]["message"]["content"]
                    
        except Exception as e:
            return f"Ошибка ИИ: {str(e)}"
    
    # ========== 7. ПОИСК В DUCKDUCKGO ==========
    async def search_duckduckgo(self, query: str, max_results: int = 10) -> List[Dict]:
        """Бесплатный поиск без API ключа"""
        from bs4 import BeautifulSoup
        
        url = f"https://html.duckduckgo.com/html/?q={query}"
        headers = {"User-Agent": "Mozilla/5.0"}
        
        results = []
        try:
            async with self.session.get(url, headers=headers, timeout=15) as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                for result in soup.select('.result')[:max_results]:
                    title_elem = result.select_one('.result__a')
                    snippet_elem = result.select_one('.result__snippet')
                    url_elem = result.select_one('.result__url')
                    
                    if title_elem:
                        results.append({
                            "title": title_elem.text.strip(),
                            "snippet": snippet_elem.text.strip() if snippet_elem else "",
                            "url": url_elem.get('href') if url_elem else ""
                        })
        except Exception as e:
            results.append({"error": str(e)})
        
        return results
    
    # ========== 8. ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ (БЕСПЛАТНО) ==========
    async def generate_image_free(self, prompt: str) -> Optional[bytes]:
        """Генерация через бесплатный HF API"""
        url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
        headers = {
            "Authorization": f"Bearer {os.getenv('HF_API_KEY')}",
            "Content-Type": "application/json"
        }
        data = {"inputs": prompt}
        
        try:
            async with self.session.post(url, headers=headers, json=data, timeout=120) as resp:
                return await resp.read()
        except:
            return None
    
    # ========== 9. АНАЛИЗ ТЕКСТА НА УТЕЧКИ ДАННЫХ ==========
    def extract_sensitive_data(self, text: str) -> Dict:
        """Извлекает email, телефоны, IP, кредитки из текста"""
        patterns = {
            "emails": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phones": r'\b(?:\+?7|8)[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}\b',
            "ips": r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
            "cards": r'\b(?:\d{4}[\s\-]?){3}\d{4}\b',
            "passports": r'\b\d{4}[\s\-]?\d{6}\b',
        }
        
        found = {}
        for name, pattern in patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                found[name] = list(set(matches))
        
        return found
