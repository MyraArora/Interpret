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

LOCAL_BACKEND_URL = "http://127.0.0.1:8000/api/spatial-map"

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
            
            # Force speech interruption so our summary takes priority over default element speech
            import speech
            speech.cancelSpeech()
            ui.message("element deepdive")
            ui.message(summary)
            
        except Exception as e:
            ui.message("Error performing element deep-dive.")
            print(f"Interpret Deep Dive Error: {e}")

    @scriptHandler.script(
        gesture="kb:NVDA+shift+g",
        description="Interpret: Multimodal vision for inaccessible graphics."
    )
    def script_multimodalVision(self, gesture):
        ui.message("Interpret: Multimodal vision analysis triggered.")