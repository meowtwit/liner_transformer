#!/usr/bin/env python3
"""
画像行列変換GUIツール
線形変換やその他の変換を行列ベースで自由に適用できるソフトウェア
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
from PIL import Image, ImageTk, ImageDraw
import cv2
import math
import re


class ImageTransformGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("画像行列変換ツール - Matrix Transform Studio")
        self.root.geometry("1500x900")
        self.root.configure(bg='#2b2b2b')

        # 変数の初期化
        self.original_image = None
        self.current_image = None
        self.display_image = None
        self.image_path = None

        # 変換順序の管理: リストの順番＝適用順（先頭が最初に適用）
        self.transform_order = ['scale', 'rotation', 'shear']

        # 各変換行列（表示用に個別管理）
        self.matrices = {
            'scale': np.eye(3),
            'rotation': np.eye(3),
            'shear': np.eye(3),
        }
        self.transform_matrix = np.eye(3)  # 合成結果

        # ビューポート制御
        self.view_offset_x = 0
        self.view_offset_y = 0
        self.view_zoom = 1.0
        self.drag_start_x = 0
        self.drag_start_y = 0

        # スライダー更新の再帰防止フラグ
        self._suppress_slider = False

        # UIの構築
        self.setup_ui()

        # 初期行列テキストを表示
        self.update_all_matrix_labels()

    # ================================================================
    # UI構築
    # ================================================================

    def setup_ui(self):
        main_frame = tk.Frame(self.root, bg='#2b2b2b')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 左パネル（コントロール） — スクロール対応
        left_panel = tk.Frame(main_frame, bg='#363636', relief=tk.RAISED,
                             borderwidth=2, width=340)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_panel.pack_propagate(False)

        left_canvas = tk.Canvas(left_panel, bg='#363636', highlightthickness=0)
        left_scrollbar = tk.Scrollbar(left_panel, orient=tk.VERTICAL,
                                     command=left_canvas.yview)
        self.left_content = tk.Frame(left_canvas, bg='#363636')

        self.left_content.bind("<Configure>",
            lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all")))
        left_canvas.create_window((0, 0), window=self.left_content, anchor=tk.NW)
        left_canvas.configure(yscrollcommand=left_scrollbar.set)

        left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # マウスホイールで左パネルをスクロール
        def _on_left_scroll(event):
            left_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        left_canvas.bind("<MouseWheel>", _on_left_scroll)
        self.left_content.bind("<MouseWheel>", _on_left_scroll)

        self.setup_control_panel(self.left_content)

        # 右パネル（画像表示）
        right_panel = tk.Frame(main_frame, bg='#363636', relief=tk.RAISED,
                              borderwidth=2)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        self.setup_display_panel(right_panel)

    def setup_control_panel(self, parent):
        header = tk.Label(parent, text="変換コントロール",
                         font=('Arial', 16, 'bold'), bg='#363636', fg='#ffffff')
        header.pack(pady=10, fill=tk.X)

        # ファイル操作
        file_frame = tk.LabelFrame(parent, text="ファイル",
                                  font=('Arial', 10, 'bold'), bg='#363636',
                                  fg='#ffffff', padx=10, pady=10)
        file_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Button(file_frame, text="画像を開く",
                 command=self.load_image, bg='#4CAF50', fg='black',
                 font=('Arial', 10), relief=tk.FLAT, padx=20, pady=5
                 ).pack(fill=tk.X, pady=2)
        tk.Button(file_frame, text="画像を保存",
                 command=self.save_image, bg='#2196F3', fg='black',
                 font=('Arial', 10), relief=tk.FLAT, padx=20, pady=5
                 ).pack(fill=tk.X, pady=2)

        # 各変換パラメータ
        self.setup_scale_controls(parent)
        self.setup_rotation_controls(parent)
        self.setup_shear_controls(parent)

        # 適用順序コントロール
        self.setup_order_controls(parent)

        # 合成結果行列
        self.setup_combined_matrix_display(parent)

        # リセット
        tk.Button(parent, text="すべてリセット",
                 command=self.reset_all, bg='#f44336', fg='black',
                 font=('Arial', 12, 'bold'), relief=tk.FLAT,
                 padx=20, pady=10).pack(fill=tk.X, padx=10, pady=10)

        # グリッド表示オプション
        self.show_grid = tk.BooleanVar(value=True)
        tk.Checkbutton(parent, text="グリッド表示",
                      variable=self.show_grid, command=self.update_display,
                      bg='#363636', fg='#ffffff', selectcolor='#2b2b2b',
                      font=('Arial', 10)).pack(pady=5)

    # ---------- 行列Entry共通作成 ----------
    def create_matrix_entries(self, parent, key, color):
        """2x2行列の個別Entryウィジェットを作成"""
        mat_frame = tk.Frame(parent, bg='#363636')
        mat_frame.pack(fill=tk.X, pady=(6, 0))

        tk.Label(mat_frame, text="行列:", bg='#363636', fg='#aaa',
                font=('Arial', 9)).pack(anchor=tk.W)

        grid = tk.Frame(mat_frame, bg='#363636')
        grid.pack(fill=tk.X, pady=2)

        entries = [[None, None], [None, None]]
        for r in range(2):
            row_frame = tk.Frame(grid, bg='#363636')
            row_frame.pack(fill=tk.X, pady=1)
            tk.Label(row_frame, text="[" if r == 0 else "[",
                    bg='#363636', fg=color, font=('Courier', 12)).pack(side=tk.LEFT)
            for c in range(2):
                e = tk.Entry(row_frame, width=10, bg='#2b2b2b', fg=color,
                           font=('Courier', 11), relief=tk.FLAT,
                           insertbackground=color, justify=tk.CENTER)
                e.pack(side=tk.LEFT, padx=2)
                entries[r][c] = e
            tk.Label(row_frame, text="]",
                    bg='#363636', fg=color, font=('Courier', 12)).pack(side=tk.LEFT)

        tk.Label(mat_frame, text="√: ⌥V | sqrt(2), 1/sqrt(2) も可",
                bg='#363636', fg='#888', font=('Arial', 8)).pack(anchor=tk.W)

        tk.Button(mat_frame, text="行列を適用",
                 command=lambda: self.apply_matrix_input(key),
                 bg=color, fg='black', relief=tk.FLAT,
                 font=('Arial', 9)).pack(fill=tk.X, pady=(2, 0))

        return entries

    # ---------- スケール ----------
    def setup_scale_controls(self, parent):
        frame = tk.LabelFrame(parent, text="[S] スケール変換",
                             font=('Arial', 10, 'bold'), bg='#363636',
                             fg='#4FC3F7', padx=10, pady=8)
        frame.pack(fill=tk.X, padx=10, pady=4)

        tk.Label(frame, text="X:", bg='#363636', fg='#fff',
                font=('Arial', 9)).pack(anchor=tk.W)
        self.scale_x = tk.DoubleVar(value=1.0)
        tk.Scale(frame, from_=0.1, to=3.0, resolution=0.05,
                orient=tk.HORIZONTAL, variable=self.scale_x,
                command=self.on_transform_change, bg='#4a4a4a',
                fg='#ffffff', highlightbackground='#363636',
                troughcolor='#2b2b2b', length=250).pack(fill=tk.X)

        tk.Label(frame, text="Y:", bg='#363636', fg='#fff',
                font=('Arial', 9)).pack(anchor=tk.W)
        self.scale_y = tk.DoubleVar(value=1.0)
        tk.Scale(frame, from_=0.1, to=3.0, resolution=0.05,
                orient=tk.HORIZONTAL, variable=self.scale_y,
                command=self.on_transform_change, bg='#4a4a4a',
                fg='#ffffff', highlightbackground='#363636',
                troughcolor='#2b2b2b', length=250).pack(fill=tk.X)

        self.scale_entries = self.create_matrix_entries(frame, 'scale', '#4FC3F7')

    # ---------- 回転 ----------
    def setup_rotation_controls(self, parent):
        frame = tk.LabelFrame(parent, text="[R] 回転変換",
                             font=('Arial', 10, 'bold'), bg='#363636',
                             fg='#81C784', padx=10, pady=8)
        frame.pack(fill=tk.X, padx=10, pady=4)

        tk.Label(frame, text="角度(度):", bg='#363636', fg='#fff',
                font=('Arial', 9)).pack(anchor=tk.W)
        self.rotation = tk.DoubleVar(value=0.0)
        tk.Scale(frame, from_=-180, to=180, resolution=1,
                orient=tk.HORIZONTAL, variable=self.rotation,
                command=self.on_transform_change, bg='#4a4a4a',
                fg='#ffffff', highlightbackground='#363636',
                troughcolor='#2b2b2b', length=250).pack(fill=tk.X)

        preset_frame = tk.Frame(frame, bg='#363636')
        preset_frame.pack(fill=tk.X, pady=4)
        for angle in [90, 120, 180, 270]:
            tk.Button(preset_frame, text=f"{angle}°",
                     command=lambda a=angle: self.set_rotation(a),
                     bg='#555555', fg='black', relief=tk.FLAT,
                     font=('Arial', 8), width=5).pack(side=tk.LEFT, padx=2)

        self.rotation_entries = self.create_matrix_entries(frame, 'rotation', '#81C784')

    # ---------- シアー ----------
    def setup_shear_controls(self, parent):
        frame = tk.LabelFrame(parent, text="[H] シアー変換（せん断）",
                             font=('Arial', 10, 'bold'), bg='#363636',
                             fg='#FFB74D', padx=10, pady=8)
        frame.pack(fill=tk.X, padx=10, pady=4)

        tk.Label(frame, text="X方向:", bg='#363636', fg='#fff',
                font=('Arial', 9)).pack(anchor=tk.W)
        self.shear_x = tk.DoubleVar(value=0.0)
        tk.Scale(frame, from_=-2.0, to=2.0, resolution=0.05,
                orient=tk.HORIZONTAL, variable=self.shear_x,
                command=self.on_transform_change, bg='#4a4a4a',
                fg='#ffffff', highlightbackground='#363636',
                troughcolor='#2b2b2b', length=250).pack(fill=tk.X)

        tk.Label(frame, text="Y方向:", bg='#363636', fg='#fff',
                font=('Arial', 9)).pack(anchor=tk.W)
        self.shear_y = tk.DoubleVar(value=0.0)
        tk.Scale(frame, from_=-2.0, to=2.0, resolution=0.05,
                orient=tk.HORIZONTAL, variable=self.shear_y,
                command=self.on_transform_change, bg='#4a4a4a',
                fg='#ffffff', highlightbackground='#363636',
                troughcolor='#2b2b2b', length=250).pack(fill=tk.X)

        self.shear_entries = self.create_matrix_entries(frame, 'shear', '#FFB74D')

    # ---------- 適用順序 ----------
    def setup_order_controls(self, parent):
        frame = tk.LabelFrame(parent, text="適用順序（上から順に適用）",
                             font=('Arial', 10, 'bold'), bg='#363636',
                             fg='#ffffff', padx=10, pady=8)
        frame.pack(fill=tk.X, padx=10, pady=4)

        self.order_frame = tk.Frame(frame, bg='#363636')
        self.order_frame.pack(fill=tk.X)

        self.rebuild_order_ui()

    def rebuild_order_ui(self):
        """適用順序UIを再構築"""
        for w in self.order_frame.winfo_children():
            w.destroy()

        NAMES = {
            'scale': ('[S] スケール', '#4FC3F7'),
            'rotation': ('[R] 回転', '#81C784'),
            'shear': ('[H] シアー', '#FFB74D'),
        }

        for i, key in enumerate(self.transform_order):
            row = tk.Frame(self.order_frame, bg='#363636')
            row.pack(fill=tk.X, pady=1)

            # 番号
            tk.Label(row, text=f"{i+1}.", bg='#363636', fg='#aaa',
                    font=('Arial', 10, 'bold'), width=2).pack(side=tk.LEFT)

            # ラベル
            name, color = NAMES[key]
            tk.Label(row, text=name, bg='#363636', fg=color,
                    font=('Arial', 10, 'bold'), width=12, anchor=tk.W
                    ).pack(side=tk.LEFT, padx=4)

            # 上下ボタン
            btn_frame = tk.Frame(row, bg='#363636')
            btn_frame.pack(side=tk.RIGHT)

            if i > 0:
                tk.Button(btn_frame, text="▲", command=lambda idx=i: self.move_order(idx, -1),
                         bg='#555555', fg='black', relief=tk.FLAT,
                         font=('Arial', 9), width=3).pack(side=tk.LEFT, padx=1)
            else:
                tk.Label(btn_frame, text="   ", bg='#363636', width=3).pack(side=tk.LEFT, padx=1)

            if i < len(self.transform_order) - 1:
                tk.Button(btn_frame, text="▼", command=lambda idx=i: self.move_order(idx, 1),
                         bg='#555555', fg='black', relief=tk.FLAT,
                         font=('Arial', 9), width=3).pack(side=tk.LEFT, padx=1)
            else:
                tk.Label(btn_frame, text="   ", bg='#363636', width=3).pack(side=tk.LEFT, padx=1)

    def move_order(self, index, direction):
        """変換の適用順序を入れ替え"""
        new_index = index + direction
        if 0 <= new_index < len(self.transform_order):
            self.transform_order[index], self.transform_order[new_index] = \
                self.transform_order[new_index], self.transform_order[index]
            self.rebuild_order_ui()
            if self.original_image is not None:
                self.apply_transform()

    # ---------- 合成行列表示 ----------
    def setup_combined_matrix_display(self, parent):
        frame = tk.LabelFrame(parent, text="合成変換行列",
                             font=('Arial', 10, 'bold'), bg='#363636',
                             fg='#ffffff', padx=10, pady=8)
        frame.pack(fill=tk.X, padx=10, pady=4)

        self.matrix_text = tk.Text(frame, height=3, width=30, bg='#2b2b2b',
                                  fg='#00ff00', font=('Courier', 9),
                                  relief=tk.FLAT, padx=5, pady=5)
        self.matrix_text.pack(fill=tk.X, pady=4)
        self.update_matrix_display()

        tk.Button(frame, text="行列を直接適用",
                 command=self.apply_custom_matrix,
                 bg='#9C27B0', fg='black', relief=tk.FLAT,
                 font=('Arial', 9)).pack(fill=tk.X)

    # ================================================================
    # 画像表示パネル
    # ================================================================

    def setup_display_panel(self, parent):
        header_frame = tk.Frame(parent, bg='#363636')
        header_frame.pack(pady=10, fill=tk.X, padx=10)
        tk.Label(header_frame, text="プレビュー",
                font=('Arial', 16, 'bold'), bg='#363636', fg='#ffffff'
                ).pack(side=tk.LEFT)
        tk.Label(header_frame,
                text="ドラッグ:移動 | スクロール:拡大縮小 | 右クリック:リセット",
                font=('Arial', 9), bg='#363636', fg='#aaaaaa'
                ).pack(side=tk.RIGHT, padx=10)

        canvas_frame = tk.Frame(parent, bg='#2b2b2b', relief=tk.SUNKEN,
                               borderwidth=2)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))
        self.canvas = tk.Canvas(canvas_frame, bg='#1e1e1e', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.setup_zoom_bar(parent)

        # マウスイベント
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Button-4>", self.on_mouse_wheel)
        self.canvas.bind("<Button-5>", self.on_mouse_wheel)
        self.canvas.bind("<Button-3>", self.reset_view)
        self.canvas.bind("<Control-MouseWheel>", self.on_ctrl_scroll)
        try:
            self.canvas.bind("<Magnify>", self.on_magnify)
        except tk.TclError:
            pass
        try:
            self.canvas.bind("<Rotate>", self.on_rotate_gesture)
        except tk.TclError:
            pass

        self.canvas.create_text(400, 300,
            text="画像を開いてください\n\n左のパネルから画像を開く",
            font=('Arial', 16), fill='#666666', tags='placeholder')

    def setup_zoom_bar(self, parent):
        zoom_bar = tk.Frame(parent, bg='#2b2b2b')
        zoom_bar.pack(fill=tk.X, padx=10, pady=(4, 10))

        tk.Button(zoom_bar, text="Fit", command=self.reset_view,
                 bg='#555555', fg='black', relief=tk.FLAT,
                 font=('Arial', 9), width=4, padx=2).pack(side=tk.LEFT, padx=(0, 8))

        zoom_right = tk.Frame(zoom_bar, bg='#2b2b2b')
        zoom_right.pack(side=tk.RIGHT)

        tk.Button(zoom_right, text=" - ", command=self.zoom_out,
                 bg='#555555', fg='black', relief=tk.FLAT,
                 font=('Arial', 12, 'bold'), width=2).pack(side=tk.LEFT, padx=2)
        for pct in [25, 50, 100, 200]:
            tk.Button(zoom_right, text=f"{pct}%",
                     command=lambda p=pct: self.set_zoom(p / 100.0),
                     bg='#444444', fg='black', relief=tk.FLAT,
                     font=('Arial', 9), width=4).pack(side=tk.LEFT, padx=1)
        tk.Button(zoom_right, text=" + ", command=self.zoom_in,
                 bg='#555555', fg='black', relief=tk.FLAT,
                 font=('Arial', 12, 'bold'), width=2).pack(side=tk.LEFT, padx=2)

        self.zoom_label = tk.Label(zoom_right, text="100%",
                                  bg='#2b2b2b', fg='#4CAF50',
                                  font=('Arial', 11, 'bold'), width=6, anchor=tk.E)
        self.zoom_label.pack(side=tk.LEFT, padx=(8, 0))

    # ================================================================
    # ファイル操作
    # ================================================================

    def load_image(self):
        file_path = filedialog.askopenfilename(
            title="画像を選択",
            filetypes=[("画像ファイル", "*.png *.jpg *.jpeg *.bmp *.gif"),
                       ("すべてのファイル", "*.*")],
            initialfile="image.png")
        if not file_path:
            return
        try:
            self.image_path = file_path
            self.original_image = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
            if self.original_image is None:
                raise ValueError("画像を読み込めませんでした")
            if len(self.original_image.shape) == 3:
                if self.original_image.shape[2] == 4:
                    self.original_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGRA2RGBA)
                else:
                    self.original_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
            self.current_image = self.original_image.copy()
            self.reset_all()
        except Exception as e:
            messagebox.showerror("エラー", f"画像の読み込みに失敗:\n{e}")

    def save_image(self):
        if self.current_image is None:
            messagebox.showwarning("警告", "保存する画像がありません")
            return
        file_path = filedialog.asksaveasfilename(
            title="画像を保存", defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("すべて", "*.*")])
        if not file_path:
            return
        try:
            if len(self.current_image.shape) == 3:
                if self.current_image.shape[2] == 4:
                    out = cv2.cvtColor(self.current_image, cv2.COLOR_RGBA2BGRA)
                else:
                    out = cv2.cvtColor(self.current_image, cv2.COLOR_RGB2BGR)
            else:
                out = self.current_image
            cv2.imwrite(file_path, out)
            messagebox.showinfo("成功", "画像を保存しました！")
        except Exception as e:
            messagebox.showerror("エラー", f"保存失敗:\n{e}")

    # ================================================================
    # 変換ロジック
    # ================================================================

    def on_transform_change(self, *args):
        if self._suppress_slider:
            return
        if self.original_image is not None:
            self.apply_transform()

    def build_individual_matrices(self):
        """各変換の行列を構築して保存"""
        sx, sy = self.scale_x.get(), self.scale_y.get()
        self.matrices['scale'] = np.array([
            [sx, 0, 0],
            [0, sy, 0],
            [0, 0, 1]
        ])

        a = math.radians(self.rotation.get())
        c, s = math.cos(a), math.sin(a)
        self.matrices['rotation'] = np.array([
            [c, -s, 0],
            [s,  c, 0],
            [0,  0, 1]
        ])

        hx, hy = self.shear_x.get(), self.shear_y.get()
        self.matrices['shear'] = np.array([
            [1,  hx, 0],
            [hy,  1, 0],
            [0,   0, 1]
        ])

    def compute_output_bounds(self, w, h, combined_linear):
        """変換後の四隅から必要な出力サイズとオフセットを計算"""
        corners = np.array([
            [0, 0, 1],
            [w, 0, 1],
            [w, h, 1],
            [0, h, 1]
        ], dtype=float).T  # 3x4

        transformed = combined_linear @ corners  # 3x4
        xs = transformed[0]
        ys = transformed[1]

        min_x, max_x = xs.min(), xs.max()
        min_y, max_y = ys.min(), ys.max()

        # パディングを追加
        pad = max(w, h) * 0.25
        min_x -= pad
        min_y -= pad
        max_x += pad
        max_y += pad

        out_w = int(math.ceil(max_x - min_x))
        out_h = int(math.ceil(max_y - min_y))

        return out_w, out_h, min_x, min_y

    def apply_transform(self):
        if self.original_image is None:
            return

        h, w = self.original_image.shape[:2]
        cx, cy = w / 2.0, h / 2.0

        self.build_individual_matrices()

        # 適用順序に従って行列を合成（画像中心を原点として変換）
        to_origin = np.array([[1, 0, -cx], [0, 1, -cy], [0, 0, 1]])
        from_origin = np.array([[1, 0, cx], [0, 1, cy], [0, 0, 1]])

        # 中心基準の合成変換を構築
        combined = np.eye(3)
        for key in self.transform_order:
            combined = self.matrices[key] @ combined

        # 完全な変換: 中心に移動 → 変換 → 戻す
        full = from_origin @ combined @ to_origin

        # 出力サイズを動的計算
        out_w, out_h, min_x, min_y = self.compute_output_bounds(w, h, full)

        # 出力画像内に収まるよう平行移動を追加
        offset = np.array([[1, 0, -min_x], [0, 1, -min_y], [0, 0, 1]])
        self.transform_matrix = offset @ full

        transform_2x3 = self.transform_matrix[:2, :]

        try:
            # RGBA変換して透明背景でワープ
            src = self.original_image
            if len(src.shape) == 2:
                src = cv2.cvtColor(src, cv2.COLOR_GRAY2RGBA)
            elif src.shape[2] == 3:
                src = cv2.cvtColor(src, cv2.COLOR_RGB2RGBA)

            self.current_image = cv2.warpAffine(
                src, transform_2x3,
                (out_w, out_h),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(0, 0, 0, 0))

            self.update_all_matrix_labels()
            self.update_matrix_display()
            self.update_display()
        except Exception as e:
            print(f"変換エラー: {e}")

    # ================================================================
    # 行列表示更新
    # ================================================================

    # ================================================================
    # √対応の値パーサー
    # ================================================================

    def parse_expr(self, text):
        """√対応の数式パーサー。例: √2, 1/√2, -√3/2, √2/2"""
        text = text.strip()
        if not text:
            return 0.0
        # √N → sqrt(N) に置換
        text = re.sub(r'√(\d+\.?\d*)', r'sqrt(\1)', text)
        # 安全な評価
        allowed = {"__builtins__": {}, "sqrt": math.sqrt, "pi": math.pi}
        return float(eval(text, allowed))

    # ================================================================
    # Entry操作
    # ================================================================

    def set_entry_value(self, entry, value):
        """Entryウィジェットの値を設定"""
        entry.delete(0, tk.END)
        # きれいな数値表示
        if abs(value - round(value)) < 1e-9:
            entry.insert(0, str(int(round(value))))
        else:
            entry.insert(0, f"{value:.4f}")

    def get_entries(self, key):
        """キーに対応するエントリ2x2リストを返す"""
        return {'scale': self.scale_entries,
                'rotation': self.rotation_entries,
                'shear': self.shear_entries}[key]

    def update_all_matrix_labels(self):
        """スライダー値から各エントリを更新"""
        for key in ['scale', 'rotation', 'shear']:
            entries = self.get_entries(key)
            m = self.matrices[key]
            for r in range(2):
                for c in range(2):
                    self.set_entry_value(entries[r][c], m[r, c])

    def apply_matrix_input(self, key):
        """各変換のEntryから行列を読み取って適用"""
        entries = self.get_entries(key)
        try:
            vals = [[self.parse_expr(entries[r][c].get()) for c in range(2)] for r in range(2)]
            m2x2 = np.array(vals)
            self.matrices[key] = np.array([
                [m2x2[0, 0], m2x2[0, 1], 0],
                [m2x2[1, 0], m2x2[1, 1], 0],
                [0, 0, 1]
            ])
            self._sync_sliders_from_matrix(key, m2x2)
            self._apply_from_matrices()
        except Exception as e:
            messagebox.showerror("エラー", f"行列の解析に失敗:\n{e}")

    def _sync_sliders_from_matrix(self, key, m2x2):
        """行列値からスライダーを逆算して同期（コールバック抑制付き）"""
        self._suppress_slider = True
        try:
            if key == 'scale':
                sx, sy = m2x2[0, 0], m2x2[1, 1]
                if 0.1 <= sx <= 3.0:
                    self.scale_x.set(sx)
                if 0.1 <= sy <= 3.0:
                    self.scale_y.set(sy)
            elif key == 'rotation':
                cos_val, sin_val = m2x2[0, 0], m2x2[1, 0]
                angle_deg = math.degrees(math.atan2(sin_val, cos_val))
                if -180 <= angle_deg <= 180:
                    self.rotation.set(angle_deg)
            elif key == 'shear':
                hx, hy = m2x2[0, 1], m2x2[1, 0]
                if -2.0 <= hx <= 2.0:
                    self.shear_x.set(hx)
                if -2.0 <= hy <= 2.0:
                    self.shear_y.set(hy)
        finally:
            self._suppress_slider = False

    def _apply_from_matrices(self):
        """self.matricesの現在値をそのまま合成して変換を適用"""
        if self.original_image is None:
            return

        h, w = self.original_image.shape[:2]
        cx, cy = w / 2.0, h / 2.0

        to_origin = np.array([[1, 0, -cx], [0, 1, -cy], [0, 0, 1]])
        from_origin = np.array([[1, 0, cx], [0, 1, cy], [0, 0, 1]])

        combined = np.eye(3)
        for key in self.transform_order:
            combined = self.matrices[key] @ combined

        full = from_origin @ combined @ to_origin

        out_w, out_h, min_x, min_y = self.compute_output_bounds(w, h, full)
        offset = np.array([[1, 0, -min_x], [0, 1, -min_y], [0, 0, 1]])
        self.transform_matrix = offset @ full

        transform_2x3 = self.transform_matrix[:2, :]

        try:
            src = self.original_image
            if len(src.shape) == 2:
                src = cv2.cvtColor(src, cv2.COLOR_GRAY2RGBA)
            elif src.shape[2] == 3:
                src = cv2.cvtColor(src, cv2.COLOR_RGB2RGBA)

            self.current_image = cv2.warpAffine(
                src, transform_2x3,
                (out_w, out_h),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(0, 0, 0, 0))

            self.update_matrix_display()
            self.update_display()
        except Exception as e:
            print(f"変換エラー: {e}")

    def update_matrix_display(self):
        self.matrix_text.delete('1.0', tk.END)
        s = "[\n"
        for row in self.transform_matrix[:2]:
            s += "  " + "  ".join([f"{x:8.3f}" for x in row]) + "\n"
        s += "]"
        self.matrix_text.insert('1.0', s)

    def apply_custom_matrix(self):
        try:
            txt = self.matrix_text.get('1.0', tk.END)
            lines = [l.strip() for l in txt.strip().strip('[]').split('\n') if l.strip()]
            if len(lines) != 2:
                raise ValueError("2行3列の行列を入力してください")
            vals = []
            for l in lines:
                v = [float(x) for x in l.replace('[', '').replace(']', '').split()]
                if len(v) != 3:
                    raise ValueError("各行は3つの値が必要です")
                vals.append(v)
            custom = np.array(vals + [[0, 0, 1]])
            if self.original_image is not None:
                h, w = self.original_image.shape[:2]
                out_w, out_h, min_x, min_y = self.compute_output_bounds(w, h, custom)
                offset = np.array([[1, 0, -min_x], [0, 1, -min_y], [0, 0, 1]])
                final = offset @ custom
                t2x3 = final[:2, :]
                src = self.original_image
                if len(src.shape) == 2:
                    src = cv2.cvtColor(src, cv2.COLOR_GRAY2RGBA)
                elif src.shape[2] == 3:
                    src = cv2.cvtColor(src, cv2.COLOR_RGB2RGBA)
                self.current_image = cv2.warpAffine(
                    src, t2x3, (out_w, out_h),
                    flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                    borderValue=(0, 0, 0, 0))
                self.transform_matrix = final
                self.update_display()
        except Exception as e:
            messagebox.showerror("エラー", f"行列適用失敗:\n{e}")

    # ================================================================
    # 表示
    # ================================================================

    def update_display(self):
        if self.current_image is None:
            return

        self.canvas.delete('all')
        self.canvas.update()
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw <= 1 or ch <= 1:
            cw, ch = 800, 600

        if self.show_grid.get():
            self.draw_grid(cw, ch)

        if len(self.current_image.shape) == 3:
            mode = 'RGBA' if self.current_image.shape[2] == 4 else 'RGB'
        else:
            mode = 'L'
        pil_image = Image.fromarray(self.current_image, mode)

        iw, ih = pil_image.size
        # 元画像のサイズを基準にスケールを計算（回転時に縮小しない）
        if self.original_image is not None:
            oh, ow = self.original_image.shape[:2]
        else:
            ow, oh = iw, ih
        base_scale = min(cw / ow, ch / oh, 1.0) * 0.85
        final_scale = base_scale * self.view_zoom

        nw = max(int(iw * final_scale), 1)
        nh = max(int(ih * final_scale), 1)
        pil_image = pil_image.resize((nw, nh), Image.Resampling.LANCZOS)

        self.display_image = ImageTk.PhotoImage(pil_image)

        x = (cw - nw) // 2 + self.view_offset_x
        y = (ch - nh) // 2 + self.view_offset_y
        self.canvas.create_image(x, y, anchor=tk.NW, image=self.display_image)

        pct = int(round(self.view_zoom * 100))
        self.zoom_label.config(text=f"{pct}%")

    def draw_grid(self, w, h):
        for x in range(0, w, 50):
            self.canvas.create_line(x, 0, x, h, fill='#333333')
        for y in range(0, h, 50):
            self.canvas.create_line(0, y, w, y, fill='#333333')
        self.canvas.create_line(w//2, 0, w//2, h, fill='#4CAF50', width=2, dash=(5,5))
        self.canvas.create_line(0, h//2, w, h//2, fill='#4CAF50', width=2, dash=(5,5))

    # ================================================================
    # ビュー操作
    # ================================================================

    def zoom_in(self):
        z = self.view_zoom * 1.25
        if z <= 10.0:
            self.view_zoom = z
            self.update_display()

    def zoom_out(self):
        z = self.view_zoom * 0.8
        if z >= 0.1:
            self.view_zoom = z
            self.update_display()

    def set_zoom(self, level):
        self.view_zoom = level
        self.view_offset_x = 0
        self.view_offset_y = 0
        self.update_display()

    def reset_view(self, event=None):
        self.view_offset_x = 0
        self.view_offset_y = 0
        self.view_zoom = 1.0
        if self.current_image is not None:
            self.update_display()

    def on_mouse_press(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def on_mouse_drag(self, event):
        if self.current_image is None:
            return
        self.view_offset_x += event.x - self.drag_start_x
        self.view_offset_y += event.y - self.drag_start_y
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.update_display()

    def on_mouse_wheel(self, event):
        if self.current_image is None:
            return
        if event.num == 4 or event.delta > 0:
            f = 1.05
        elif event.num == 5 or event.delta < 0:
            f = 0.95
        else:
            return
        z = self.view_zoom * f
        if 0.1 <= z <= 10.0:
            self.view_zoom = z
            self.update_display()

    def on_ctrl_scroll(self, event):
        if self.current_image is None:
            return
        f = 1.15 if event.delta > 0 else 0.85
        z = self.view_zoom * f
        if 0.1 <= z <= 10.0:
            self.view_zoom = z
            self.update_display()

    def on_magnify(self, event):
        if self.current_image is None:
            return
        z = self.view_zoom * (1.0 + event.delta)
        if 0.1 <= z <= 10.0:
            self.view_zoom = z
            self.update_display()

    def on_rotate_gesture(self, event):
        if self.current_image is None:
            return
        r = self.rotation.get() + event.delta
        while r > 180: r -= 360
        while r < -180: r += 360
        self.rotation.set(r)

    # ================================================================
    # リセット
    # ================================================================

    def reset_scale(self):
        self.scale_x.set(1.0)
        self.scale_y.set(1.0)

    def set_rotation(self, angle):
        self.rotation.set(angle)

    def reset_all(self):
        self.scale_x.set(1.0)
        self.scale_y.set(1.0)
        self.rotation.set(0.0)
        self.shear_x.set(0.0)
        self.shear_y.set(0.0)
        self.transform_order = ['scale', 'rotation', 'shear']
        self.rebuild_order_ui()
        self.transform_matrix = np.eye(3)
        for k in self.matrices:
            self.matrices[k] = np.eye(3)

        if self.original_image is not None:
            self.current_image = self.original_image.copy()
            self.reset_view()
            self.update_all_matrix_labels()
            self.update_display()
            self.update_matrix_display()


def main():
    root = tk.Tk()
    app = ImageTransformGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
