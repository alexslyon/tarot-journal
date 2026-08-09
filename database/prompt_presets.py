"""
Prompt presets — named, editable versions of the AI assistants'
system prompts (Mirror / Analyst / Scribe).

The shipped prompts live in the frontend as built-in defaults; this
table only stores user-authored variants. Which preset is active per
assistant is a settings key (active_prompt_preset_<feature>, empty =
built-in default), so switching versions is instant and reversible.
"""

from __future__ import annotations


class PromptPresetsMixin:

    def get_prompt_presets(self, feature: str):
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT * FROM prompt_presets WHERE feature = ? ORDER BY name',
            (feature,),
        )
        return cursor.fetchall()

    def get_prompt_preset(self, preset_id: int):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM prompt_presets WHERE id = ?', (preset_id,))
        return cursor.fetchone()

    def add_prompt_preset(self, feature: str, name: str, content: str) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO prompt_presets (feature, name, content) VALUES (?, ?, ?)',
            (feature, name, content),
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_prompt_preset(self, preset_id: int, name: str = None,
                             content: str = None):
        sets, params = [], []
        if name is not None:
            sets.append('name = ?')
            params.append(name)
        if content is not None:
            sets.append('content = ?')
            params.append(content)
        if not sets:
            return
        sets.append("updated_at = datetime('now')")
        params.append(preset_id)
        cursor = self.conn.cursor()
        cursor.execute(
            f"UPDATE prompt_presets SET {', '.join(sets)} WHERE id = ?",
            params,
        )
        self.conn.commit()

    def delete_prompt_preset(self, preset_id: int):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM prompt_presets WHERE id = ?', (preset_id,))
        self.conn.commit()

    def get_active_prompt_preset_id(self, feature: str) -> int | None:
        raw = self.get_setting(f'active_prompt_preset_{feature}') or ''
        return int(raw) if raw.isdigit() else None

    def set_active_prompt_preset_id(self, feature: str, preset_id: int | None):
        self.set_setting(
            f'active_prompt_preset_{feature}',
            str(preset_id) if preset_id else '',
        )
