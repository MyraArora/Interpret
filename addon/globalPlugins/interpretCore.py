# -*- coding: utf-8 -*-

import globalPluginHandler
import scriptHandler
import ui
import api
import controlTypes
import json
import urllib.request
import urllib.error
import threading
import speech

LOCAL_BACKEND_URL = "http://127.0.0.1:8000/api/spatial-map"
VISION_BACKEND_URL = "http://127.0.0.1:8000/api/multimodal-vision"

class GlobalPlugin(globalPluginHandler.GlobalPlugin):

    @scriptHandler.script(
        gesture="kb:NVDA+shift+i",
        description="Interpret: Scan viewport spatial map and navigation guide."
    )
    def script_spatialMap(self, gesture):
        ui.message("Scanning viewport spatial layout...")
        
        def task():
            try:
                spatial_data = self._harvest_viewport_tree()
                if not spatial_data:
                    ui.message("No interactive elements detected in current viewport.")
                    return
                
                overview = self._query_local_backend(spatial_data)
                speech.cancelSpeech()
                ui.message(overview)
            except Exception as e:
                ui.message("Error generating spatial map.")
                print(f"Interpret Spatial Map Error: {e}")

        threading.Thread(target=task, daemon=True).start()

    def _harvest_viewport_tree(self):
        focus_obj = api.getFocusObject()
        fg_obj = api.getForegroundObject()
        
        root_obj = fg_obj if fg_obj else focus_obj
        interactive_elements = []
        visited = set()

        def extract_info(obj):
            try:
                name = getattr(obj, 'name', '') or ''
                role = getattr(obj, 'role', None)
                role_name = controlTypes.speech.getRoleName(role) if role is not None and hasattr(controlTypes, 'speech') else str(role)
                location = getattr(obj, 'location', None)
                
                return {
                    "name": name.strip(),
                    "role": role_name,
                    "location": location
                }
            except Exception:
                return None

        def walk_obj(obj, depth=0):
            if not obj or depth > 5 or len(interactive_elements) >= 35:
                return
            
            obj_hash = hash(obj)
            if obj_hash in visited:
                return
            visited.add(obj_hash)

            try:
                info = extract_info(obj)
                if info and info["location"] and info["location"].width > 0 and info["location"].height > 0:
                    if info["name"] or info["role"]:
                        interactive_elements.append({
                            "role": info["role"],
                            "name": info["name"],
                            "bounds": {
                                "left": info["location"].left,
                                "top": info["location"].top,
                                "width": info["location"].width,
                                "height": info["location"].height
                            }
                        })

                child = getattr(obj, 'firstChild', None)
                while child:
                    walk_obj(child, depth + 1)
                    child = getattr(child, 'next', None)

            except Exception:
                pass

        walk_obj(root_obj)

        if not interactive_elements and focus_obj:
            curr = focus_obj
            for _ in range(15):
                if curr:
                    info = extract_info(curr)
                    if info and info["location"]:
                        interactive_elements.append({
                            "role": info["role"],
                            "name": info["name"],
                            "bounds": {
                                "left": info["location"].left,
                                "top": info["location"].top,
                                "width": info["location"].width,
                                "height": info["location"].height
                            }
                        })
                curr = getattr(curr, 'next', None)

        return interactive_elements

    def _query_local_backend(self, spatial_data):
        payload = {"elements": spatial_data}
        req = urllib.request.Request(
            LOCAL_BACKEND_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                return res_data.get("overview", "Spatial guide generated.")
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8', errors='ignore')
            return f"Backend HTTP Error {e.code}: {error_body[:60]}"
        except Exception as e:
            return f"Local backend connection error. Make sure FastAPI server is running."

    @scriptHandler.script(
        gesture="kb:NVDA+shift+o",
        description="Interpret: Targeted element deep-dive."
    )
    def script_elementDeepDive(self, gesture):
        try:
            focus_obj = api.getFocusObject()
            if not focus_obj:
                ui.message("No active focus object found.")
                return

            name = getattr(focus_obj, 'name', '') or 'Unnamed'
            role = getattr(focus_obj, 'role', None)
            role_name = controlTypes.speech.getRoleName(role) if role is not None and hasattr(controlTypes, 'speech') else str(role)
            value = getattr(focus_obj, 'value', '') or ''
            description = getattr(focus_obj, 'description', '') or ''
            
            states = []
            if hasattr(focus_obj, 'states'):
                for state in focus_obj.states:
                    try:
                        state_name = controlTypes.speech.getStateName(state) if hasattr(controlTypes.speech, 'getStateName') else str(state)
                        if state_name:
                            states.append(state_name)
                    except Exception:
                        pass

            value_part = f", value: {value}" if value else ""
            states_part = f", states: {', '.join(states)}" if states else ""
            desc_part = f" {description}" if description else ""

            summary = f"{name}, {role_name}{value_part}{states_part}.{desc_part}"
            
            speech.cancelSpeech()
            ui.message(summary)
            
        except Exception as e:
            ui.message("Error performing element deep-dive.")
            print(f"Interpret Deep Dive Error: {e}")

    @scriptHandler.script(
        gesture="kb:NVDA+shift+g",
        description="Interpret: Multimodal vision for inaccessible graphics."
    )
    def script_multimodalVision(self, gesture):
        ui.message("Capturing active window for vision analysis...")
        
        def task():
            try:
                import ctypes
                import ctypes.wintypes
                import base64

                user32 = ctypes.windll.user32
                gdi32 = ctypes.windll.gdi32

                hwnd = user32.GetForegroundWindow()
                rect = ctypes.wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))

                left = rect.left
                top = rect.top
                width = rect.right - rect.left
                height = rect.bottom - rect.top

                screen_w = user32.GetSystemMetrics(0)
                screen_h = user32.GetSystemMetrics(1)
                
                if width <= 50 or height <= 50 or left < -3000 or top < -3000:
                    left, top = 0, 0
                    width, height = screen_w, screen_h

                left = max(0, min(left, screen_w - 50))
                top = max(0, min(top, screen_h - 50))
                width = min(width, screen_w - left)
                height = min(height, screen_h - top)

                h_screen_dc = user32.GetDC(0)
                h_mem_dc = gdi32.CreateCompatibleDC(h_screen_dc)
                h_bitmap = gdi32.CreateCompatibleBitmap(h_screen_dc, width, height)
                gdi32.SelectObject(h_mem_dc, h_bitmap)
                gdi32.BitBlt(h_mem_dc, 0, 0, width, height, h_screen_dc, left, top, 0x00CC0020)

                class BITMAPINFOHEADER(ctypes.Structure):
                    _fields_ = [
                        ("biSize", ctypes.wintypes.DWORD),
                        ("biWidth", ctypes.wintypes.LONG),
                        ("biHeight", ctypes.wintypes.LONG),
                        ("biPlanes", ctypes.wintypes.WORD),
                        ("biBitCount", ctypes.wintypes.WORD),
                        ("biCompression", ctypes.wintypes.DWORD),
                        ("biSizeImage", ctypes.wintypes.DWORD),
                        ("biXPelsPerMeter", ctypes.wintypes.LONG),
                        ("biYPelsPerMeter", ctypes.wintypes.LONG),
                        ("biClrUsed", ctypes.wintypes.DWORD),
                        ("biClrImportant", ctypes.wintypes.DWORD)
                    ]

                bih = BITMAPINFOHEADER()
                bih.biSize = ctypes.sizeof(BITMAPINFOHEADER)
                bih.biWidth = width
                bih.biHeight = -height
                bih.biPlanes = 1
                bih.biBitCount = 24

                buffer_size = width * height * 3
                buffer = ctypes.create_string_buffer(buffer_size)
                gdi32.GetDIBits(h_screen_dc, h_bitmap, 0, height, buffer, ctypes.byref(bih), 0)

                gdi32.DeleteObject(h_bitmap)
                gdi32.DeleteDC(h_mem_dc)
                user32.ReleaseDC(0, h_screen_dc)

                encoded_image = base64.b64encode(buffer.raw).decode('utf-8')

                payload = {
                    "image_base64": encoded_image,
                    "width": width,
                    "height": height
                }
                
                req = urllib.request.Request(
                    VISION_BACKEND_URL,
                    data=json.dumps(payload).encode('utf-8'),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )

                with urllib.request.urlopen(req, timeout=30) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                    overview = res_data.get("overview", "Vision analysis complete.")
                    
                    speech.cancelSpeech()
                    ui.message(overview)

            except Exception as e:
                ui.message("Error performing window vision analysis.")
                print(f"Interpret Window Vision Error: {e}")

        threading.Thread(target=task, daemon=True).start()