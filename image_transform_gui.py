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


class ImageTransformGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("画像行列変換ツール - Matrix Transform Studio")
        self.root.geometry("1400x900")
        self.root.configure(bg='#2b2b2b')

        # 変数の初期化
        self.original_image = None
        self.current_image = None
        self.display_image = None
        self.image_path = None

        # 変換行列の初期化（単位行列）
        self.transform_matrix = np.eye(3)

        # ビューポート制御（パン・ズーム用）
        self.view_offset_x = 0
        self.view_offset_y = 0
        self.view_zoom = 1.0
        self.drag_start_x = 0
        self.drag_start_y = 0

        # UIの構築
        self.setup_ui()

    def setup_ui(self):
        """UIのセットアップ"""
        # メインフレーム
        main_frame = tk.Frame(self.root, bg='#2b2b2b')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 左パネル（コントロール）
        left_panel = tk.Frame(main_frame, bg='#363636', relief=tk.RAISED, borderwidth=2)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 5))

        # 右パネル（画像表示）
        right_panel = tk.Frame(main_frame, bg='#363636', relief=tk.RAISED, borderwidth=2)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # ===== 左パネルの内容 =====
        self.setup_control_panel(left_panel)

        # ===== 右パネルの内容 =====
        self.setup_display_panel(right_panel)

    def setup_control_panel(self, parent):
        """コントロールパネルのセットアップ"""
        # ヘッダー
        header = tk.Label(parent, text="変換コントロール",
                         font=('Arial', 16, 'bold'), bg='#363636', fg='#ffffff')
        header.pack(pady=10)

        # ファイル操作
        file_frame = tk.LabelFrame(parent, text="ファイル",
                                  font=('Arial', 10, 'bold'), bg='#363636',
                                  fg='#ffffff', padx=10, pady=10)
        file_frame.pack(fill=tk.X, padx=10, pady=5)

        btn_load = tk.Button(file_frame, text="📁 画像を開く",
                           command=self.load_image, bg='#4CAF50', fg='black',
                           font=('Arial', 10), relief=tk.FLAT, padx=20, pady=5)
        btn_load.pack(fill=tk.X, pady=2)

        btn_save = tk.Button(file_frame, text="💾 画像を保存",
                           command=self.save_image, bg='#2196F3', fg='black',
                           font=('Arial', 10), relief=tk.FLAT, padx=20, pady=5)
        btn_save.pack(fill=tk.X, pady=2)

        # スケール変換
        self.setup_scale_controls(parent)

        # 回転変換
        self.setup_rotation_controls(parent)

        # シアー変換
        self.setup_shear_controls(parent)

        # カスタム行列
        self.setup_matrix_controls(parent)

        # リセットボタン
        btn_reset = tk.Button(parent, text="🔄 すべてリセット",
                            command=self.reset_all, bg='#f44336', fg='black',
                            font=('Arial', 12, 'bold'), relief=tk.FLAT,
                            padx=20, pady=10)
        btn_reset.pack(fill=tk.X, padx=10, pady=10)

        # グリッド表示オプション
        self.show_grid = tk.BooleanVar(value=True)
        chk_grid = tk.Checkbutton(parent, text="グリッド表示",
                                 variable=self.show_grid, command=self.update_display,
                                 bg='#363636', fg='#ffffff', selectcolor='#2b2b2b',
                                 font=('Arial', 10))
        chk_grid.pack(pady=5)

    def setup_scale_controls(self, parent):
        """スケール変換コントロール"""
        frame = tk.LabelFrame(parent, text="スケール変換",
                             font=('Arial', 10, 'bold'), bg='#363636',
                             fg='#ffffff', padx=10, pady=10)
        frame.pack(fill=tk.X, padx=10, pady=5)

        # X方向スケール
        tk.Label(frame, text="X軸スケール:", bg='#363636',
                fg='#ffffff', font=('Arial', 9)).pack(anchor=tk.W)

        self.scale_x = tk.DoubleVar(value=1.0)
        scale_x_slider = tk.Scale(frame, from_=0.1, to=3.0, resolution=0.1,
                                 orient=tk.HORIZONTAL, variable=self.scale_x,
                                 command=self.on_transform_change, bg='#4a4a4a',
                                 fg='#ffffff', highlightbackground='#363636',
                                 troughcolor='#2b2b2b', length=250)
        scale_x_slider.pack(fill=tk.X)

        # Y方向スケール
        tk.Label(frame, text="Y軸スケール:", bg='#363636',
                fg='#ffffff', font=('Arial', 9)).pack(anchor=tk.W, pady=(10, 0))

        self.scale_y = tk.DoubleVar(value=1.0)
        scale_y_slider = tk.Scale(frame, from_=0.1, to=3.0, resolution=0.1,
                                 orient=tk.HORIZONTAL, variable=self.scale_y,
                                 command=self.on_transform_change, bg='#4a4a4a',
                                 fg='#ffffff', highlightbackground='#363636',
                                 troughcolor='#2b2b2b', length=250)
        scale_y_slider.pack(fill=tk.X)

        # 等倍リセットボタン
        btn_reset_scale = tk.Button(frame, text="1:1にリセット",
                                   command=lambda: self.reset_scale(),
                                   bg='#555555', fg='black', relief=tk.FLAT,
                                   font=('Arial', 8))
        btn_reset_scale.pack(pady=5)

    def setup_rotation_controls(self, parent):
        """回転変換コントロール"""
        frame = tk.LabelFrame(parent, text="回転変換",
                             font=('Arial', 10, 'bold'), bg='#363636',
                             fg='#ffffff', padx=10, pady=10)
        frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(frame, text="回転角度（度）:", bg='#363636',
                fg='#ffffff', font=('Arial', 9)).pack(anchor=tk.W)

        self.rotation = tk.DoubleVar(value=0.0)
        rotation_slider = tk.Scale(frame, from_=-180, to=180, resolution=1,
                                  orient=tk.HORIZONTAL, variable=self.rotation,
                                  command=self.on_transform_change, bg='#4a4a4a',
                                  fg='#ffffff', highlightbackground='#363636',
                                  troughcolor='#2b2b2b', length=250)
        rotation_slider.pack(fill=tk.X)

        # プリセット回転ボタン
        preset_frame = tk.Frame(frame, bg='#363636')
        preset_frame.pack(fill=tk.X, pady=5)

        for angle in [90, 120, 180, 270]:
            btn = tk.Button(preset_frame, text=f"{angle}°",
                          command=lambda a=angle: self.set_rotation(a),
                          bg='#555555', fg='black', relief=tk.FLAT,
                          font=('Arial', 8), width=5)
            btn.pack(side=tk.LEFT, padx=2)

    def setup_shear_controls(self, parent):
        """シアー変換コントロール"""
        frame = tk.LabelFrame(parent, text="シアー変換（せん断）",
                             font=('Arial', 10, 'bold'), bg='#363636',
                             fg='#ffffff', padx=10, pady=10)
        frame.pack(fill=tk.X, padx=10, pady=5)

        # X方向シアー
        tk.Label(frame, text="X方向シアー:", bg='#363636',
                fg='#ffffff', font=('Arial', 9)).pack(anchor=tk.W)

        self.shear_x = tk.DoubleVar(value=0.0)
        shear_x_slider = tk.Scale(frame, from_=-2.0, to=2.0, resolution=0.1,
                                 orient=tk.HORIZONTAL, variable=self.shear_x,
                                 command=self.on_transform_change, bg='#4a4a4a',
                                 fg='#ffffff', highlightbackground='#363636',
                                 troughcolor='#2b2b2b', length=250)
        shear_x_slider.pack(fill=tk.X)

        # Y方向シアー
        tk.Label(frame, text="Y方向シアー:", bg='#363636',
                fg='#ffffff', font=('Arial', 9)).pack(anchor=tk.W, pady=(10, 0))

        self.shear_y = tk.DoubleVar(value=0.0)
        shear_y_slider = tk.Scale(frame, from_=-2.0, to=2.0, resolution=0.1,
                                 orient=tk.HORIZONTAL, variable=self.shear_y,
                                 command=self.on_transform_change, bg='#4a4a4a',
                                 fg='#ffffff', highlightbackground='#363636',
                                 troughcolor='#2b2b2b', length=250)
        shear_y_slider.pack(fill=tk.X)

    def setup_matrix_controls(self, parent):
        """カスタム行列コントロール"""
        frame = tk.LabelFrame(parent, text="カスタム変換行列",
                             font=('Arial', 10, 'bold'), bg='#363636',
                             fg='#ffffff', padx=10, pady=10)
        frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(frame, text="現在の変換行列:", bg='#363636',
                fg='#ffffff', font=('Arial', 9)).pack(anchor=tk.W)

        self.matrix_text = tk.Text(frame, height=3, width=30, bg='#2b2b2b',
                                  fg='#00ff00', font=('Courier', 9),
                                  relief=tk.FLAT, padx=5, pady=5)
        self.matrix_text.pack(fill=tk.X, pady=5)
        self.update_matrix_display()

        btn_apply_matrix = tk.Button(frame, text="行列を適用",
                                    command=self.apply_custom_matrix,
                                    bg='#9C27B0', fg='black', relief=tk.FLAT,
                                    font=('Arial', 9))
        btn_apply_matrix.pack(fill=tk.X)

    def setup_display_panel(self, parent):
        """画像表示パネルのセットアップ"""
        # ヘッダー＋操作説明
        header_frame = tk.Frame(parent, bg='#363636')
        header_frame.pack(pady=10, fill=tk.X, padx=10)

        header = tk.Label(header_frame, text="プレビュー",
                         font=('Arial', 16, 'bold'), bg='#363636', fg='#ffffff')
        header.pack(side=tk.LEFT)

        # 操作説明
        help_text = tk.Label(header_frame,
                           text="🖱️ ドラッグ:移動 | ホイール/ピンチ:拡大縮小 | 2本指回転:画像回転 | 右クリック:リセット",
                           font=('Arial', 9), bg='#363636', fg='#aaaaaa')
        help_text.pack(side=tk.RIGHT, padx=10)

        # キャンバスフレーム
        canvas_frame = tk.Frame(parent, bg='#2b2b2b', relief=tk.SUNKEN, borderwidth=2)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))

        # キャンバス
        self.canvas = tk.Canvas(canvas_frame, bg='#1e1e1e',
                               highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # ズームコントロールバー
        self.setup_zoom_bar(parent)

        # マウスイベントのバインド
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Button-4>", self.on_mouse_wheel)  # Linux用
        self.canvas.bind("<Button-5>", self.on_mouse_wheel)  # Linux用
        self.canvas.bind("<Button-3>", self.reset_view)  # 右クリックでビューリセット

        # タッチパッドジェスチャーのバインド（Tkバージョンにより利用可否が異なる）
        try:
            self.canvas.bind("<Magnify>", self.on_magnify)
        except tk.TclError:
            pass  # Magnifyイベント非対応のTkバージョン
        try:
            self.canvas.bind("<Rotate>", self.on_rotate_gesture)
        except tk.TclError:
            pass  # Rotateイベント非対応のTkバージョン

        # macOS: トラックパッドの2本指スクロール（ピンチ代替）
        # Ctrl+スクロールでズーム（ブラウザと同じ操作感）
        self.canvas.bind("<Control-MouseWheel>", self.on_ctrl_scroll)

        # 初期メッセージ
        self.canvas.create_text(400, 300,
                               text="画像を開いてください\n\n📁 左のパネルから画像を開く",
                               font=('Arial', 16), fill='#666666',
                               tags='placeholder')

    def setup_zoom_bar(self, parent):
        """ズームコントロールバーのセットアップ"""
        zoom_bar = tk.Frame(parent, bg='#2b2b2b')
        zoom_bar.pack(fill=tk.X, padx=10, pady=(4, 10))

        # 左側: ビューリセット
        btn_fit = tk.Button(zoom_bar, text="Fit", command=self.reset_view,
                           bg='#555555', fg='black', relief=tk.FLAT,
                           font=('Arial', 9), width=4, padx=2)
        btn_fit.pack(side=tk.LEFT, padx=(0, 8))

        # 右側にズームコントロールをまとめる
        zoom_right = tk.Frame(zoom_bar, bg='#2b2b2b')
        zoom_right.pack(side=tk.RIGHT)

        # [-] ボタン
        btn_zoom_out = tk.Button(zoom_right, text=" - ", command=self.zoom_out,
                                bg='#555555', fg='black', relief=tk.FLAT,
                                font=('Arial', 12, 'bold'), width=2)
        btn_zoom_out.pack(side=tk.LEFT, padx=2)

        # 縮尺プリセットボタン
        for pct in [25, 50, 100, 200]:
            btn = tk.Button(zoom_right, text=f"{pct}%",
                          command=lambda p=pct: self.set_zoom(p / 100.0),
                          bg='#444444', fg='black', relief=tk.FLAT,
                          font=('Arial', 9), width=4)
            btn.pack(side=tk.LEFT, padx=1)

        # [+] ボタン
        btn_zoom_in = tk.Button(zoom_right, text=" + ", command=self.zoom_in,
                               bg='#555555', fg='black', relief=tk.FLAT,
                               font=('Arial', 12, 'bold'), width=2)
        btn_zoom_in.pack(side=tk.LEFT, padx=2)

        # ズーム表示ラベル
        self.zoom_label = tk.Label(zoom_right, text="100%",
                                  bg='#2b2b2b', fg='#4CAF50',
                                  font=('Arial', 11, 'bold'), width=6, anchor=tk.E)
        self.zoom_label.pack(side=tk.LEFT, padx=(8, 0))

    def zoom_in(self):
        """ズームイン"""
        new_zoom = self.view_zoom * 1.25
        if new_zoom <= 10.0:
            self.view_zoom = new_zoom
            self.update_display()

    def zoom_out(self):
        """ズームアウト"""
        new_zoom = self.view_zoom * 0.8
        if new_zoom >= 0.1:
            self.view_zoom = new_zoom
            self.update_display()

    def set_zoom(self, level):
        """ズームを指定倍率に設定"""
        self.view_zoom = level
        self.view_offset_x = 0
        self.view_offset_y = 0
        self.update_display()

    def load_image(self):
        """画像を読み込む"""
        file_path = filedialog.askopenfilename(
            title="画像を選択",
            filetypes=[
                ("画像ファイル", "*.png *.jpg *.jpeg *.bmp *.gif"),
                ("すべてのファイル", "*.*")
            ],
            initialfile="image.png"
        )

        if file_path:
            try:
                self.image_path = file_path
                self.original_image = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)

                if self.original_image is None:
                    raise ValueError("画像を読み込めませんでした")

                # BGRをRGBに変換（アルファチャンネルがある場合は保持）
                if len(self.original_image.shape) == 3:
                    if self.original_image.shape[2] == 4:
                        self.original_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGRA2RGBA)
                    else:
                        self.original_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)

                self.current_image = self.original_image.copy()
                self.reset_all()
                messagebox.showinfo("成功", "画像を読み込みました！")
            except Exception as e:
                messagebox.showerror("エラー", f"画像の読み込みに失敗しました:\n{str(e)}")

    def save_image(self):
        """画像を保存"""
        if self.current_image is None:
            messagebox.showwarning("警告", "保存する画像がありません")
            return

        file_path = filedialog.asksaveasfilename(
            title="画像を保存",
            defaultextension=".png",
            filetypes=[
                ("PNG画像", "*.png"),
                ("JPEG画像", "*.jpg"),
                ("すべてのファイル", "*.*")
            ]
        )

        if file_path:
            try:
                # RGBをBGRに戻して保存
                if len(self.current_image.shape) == 3:
                    if self.current_image.shape[2] == 4:
                        img_to_save = cv2.cvtColor(self.current_image, cv2.COLOR_RGBA2BGRA)
                    else:
                        img_to_save = cv2.cvtColor(self.current_image, cv2.COLOR_RGB2BGR)
                else:
                    img_to_save = self.current_image

                cv2.imwrite(file_path, img_to_save)
                messagebox.showinfo("成功", "画像を保存しました！")
            except Exception as e:
                messagebox.showerror("エラー", f"画像の保存に失敗しました:\n{str(e)}")

    def on_transform_change(self, *args):
        """変換パラメータが変更されたときの処理"""
        if self.original_image is None:
            return

        self.apply_transform()

    def apply_transform(self):
        """現在のパラメータで変換を適用"""
        if self.original_image is None:
            return

        # 変換行列を構築
        h, w = self.original_image.shape[:2]

        # 出力画像サイズを大きく確保（見切れを防ぐ）
        output_w = w * 4
        output_h = h * 4
        output_center_x = output_w / 2
        output_center_y = output_h / 2

        # 1. 元画像の中心を出力画像の中心に移動
        translate_to_output_center = np.array([
            [1, 0, output_center_x - w / 2],
            [0, 1, output_center_y - h / 2],
            [0, 0, 1]
        ])

        # 2. 出力中心を原点に移動
        translate_to_origin = np.array([
            [1, 0, -output_center_x],
            [0, 1, -output_center_y],
            [0, 0, 1]
        ])

        # 3. スケール変換
        scale_matrix = np.array([
            [self.scale_x.get(), 0, 0],
            [0, self.scale_y.get(), 0],
            [0, 0, 1]
        ])

        # 4. 回転変換
        angle_rad = math.radians(self.rotation.get())
        cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
        rotation_matrix = np.array([
            [cos_a, -sin_a, 0],
            [sin_a, cos_a, 0],
            [0, 0, 1]
        ])

        # 5. シアー変換
        shear_matrix = np.array([
            [1, self.shear_x.get(), 0],
            [self.shear_y.get(), 1, 0],
            [0, 0, 1]
        ])

        # 6. 原点から出力中心に戻す
        translate_back = np.array([
            [1, 0, output_center_x],
            [0, 1, output_center_y],
            [0, 0, 1]
        ])

        # 全変換を合成（右から左へ適用）
        # まず元画像を出力中心に配置 → 中心を原点に → 変換 → 中心に戻す
        self.transform_matrix = translate_back @ shear_matrix @ rotation_matrix @ scale_matrix @ translate_to_origin @ translate_to_output_center

        # OpenCV用の2x3行列に変換
        transform_2x3 = self.transform_matrix[:2, :]

        # 変換を適用
        try:
            self.current_image = cv2.warpAffine(
                self.original_image,
                transform_2x3,
                (output_w, output_h),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(0, 0, 0, 0) if len(self.original_image.shape) == 3 and self.original_image.shape[2] == 4 else (255, 255, 255)
            )

            self.update_display()
            self.update_matrix_display()
        except Exception as e:
            print(f"変換エラー: {e}")

    def update_display(self):
        """キャンバスに画像を表示"""
        if self.current_image is None:
            return

        self.canvas.delete('all')

        # キャンバスのサイズを取得
        self.canvas.update()
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width, canvas_height = 800, 600

        # グリッドを描画（オプション）
        if self.show_grid.get():
            self.draw_grid(canvas_width, canvas_height)

        # 画像をPIL形式に変換
        if len(self.current_image.shape) == 3:
            if self.current_image.shape[2] == 4:
                pil_image = Image.fromarray(self.current_image, 'RGBA')
            else:
                pil_image = Image.fromarray(self.current_image, 'RGB')
        else:
            pil_image = Image.fromarray(self.current_image, 'L')

        # 基本スケールを計算（画像全体が収まるように）
        img_width, img_height = pil_image.size
        base_scale = min(canvas_width / img_width, canvas_height / img_height, 1.0) * 0.3

        # ビューズームを適用
        final_scale = base_scale * self.view_zoom

        new_width = int(img_width * final_scale)
        new_height = int(img_height * final_scale)

        pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Tkinter用に変換
        self.display_image = ImageTk.PhotoImage(pil_image)

        # キャンバスの中央に配置（ビューオフセットを適用）
        x = (canvas_width - new_width) // 2 + self.view_offset_x
        y = (canvas_height - new_height) // 2 + self.view_offset_y

        self.canvas.create_image(x, y, anchor=tk.NW, image=self.display_image)

        # ズームラベルを更新
        pct = int(round(self.view_zoom * 100))
        self.zoom_label.config(text=f"{pct}%")

    def draw_grid(self, width, height):
        """グリッドを描画"""
        grid_size = 50

        # 縦線
        for x in range(0, width, grid_size):
            self.canvas.create_line(x, 0, x, height, fill='#333333', width=1)

        # 横線
        for y in range(0, height, grid_size):
            self.canvas.create_line(0, y, width, y, fill='#333333', width=1)

        # 中央線（強調）
        self.canvas.create_line(width // 2, 0, width // 2, height,
                               fill='#4CAF50', width=2, dash=(5, 5))
        self.canvas.create_line(0, height // 2, width, height // 2,
                               fill='#4CAF50', width=2, dash=(5, 5))

    def update_matrix_display(self):
        """変換行列の表示を更新"""
        self.matrix_text.delete('1.0', tk.END)
        matrix_str = "[\n"
        for row in self.transform_matrix[:2]:  # 2x3行列のみ表示
            matrix_str += "  " + "  ".join([f"{x:7.3f}" for x in row]) + "\n"
        matrix_str += "]"
        self.matrix_text.insert('1.0', matrix_str)

    def apply_custom_matrix(self):
        """カスタム行列を適用"""
        try:
            matrix_str = self.matrix_text.get('1.0', tk.END)
            # 簡易的なパース（改良の余地あり）
            lines = [line.strip() for line in matrix_str.strip().strip('[]').split('\n') if line.strip()]

            if len(lines) != 2:
                raise ValueError("2行3列の行列を入力してください")

            matrix_values = []
            for line in lines:
                values = [float(x) for x in line.replace('[', '').replace(']', '').split()]
                if len(values) != 3:
                    raise ValueError("各行は3つの値を含む必要があります")
                matrix_values.append(values)

            # 3x3行列に拡張
            custom_matrix = np.array(matrix_values + [[0, 0, 1]])
            self.transform_matrix = custom_matrix

            # 変換を適用
            if self.original_image is not None:
                h, w = self.original_image.shape[:2]
                output_w = w * 4
                output_h = h * 4

                # 元画像を出力画像の中心に配置するための変換を追加
                output_center_x = output_w / 2
                output_center_y = output_h / 2

                translate_to_output_center = np.array([
                    [1, 0, output_center_x - w / 2],
                    [0, 1, output_center_y - h / 2],
                    [0, 0, 1]
                ])

                # カスタム行列と配置変換を合成
                final_matrix = self.transform_matrix @ translate_to_output_center
                transform_2x3 = final_matrix[:2, :]

                self.current_image = cv2.warpAffine(
                    self.original_image,
                    transform_2x3,
                    (output_w, output_h),
                    flags=cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_CONSTANT,
                    borderValue=(0, 0, 0, 0) if len(self.original_image.shape) == 3 and self.original_image.shape[2] == 4 else (255, 255, 255)
                )

                self.update_display()
                messagebox.showinfo("成功", "カスタム行列を適用しました！")
        except Exception as e:
            messagebox.showerror("エラー", f"行列の適用に失敗しました:\n{str(e)}")

    def reset_scale(self):
        """スケールをリセット"""
        self.scale_x.set(1.0)
        self.scale_y.set(1.0)

    def set_rotation(self, angle):
        """回転角度を設定"""
        self.rotation.set(angle)

    def reset_all(self):
        """すべてのパラメータをリセット"""
        self.scale_x.set(1.0)
        self.scale_y.set(1.0)
        self.rotation.set(0.0)
        self.shear_x.set(0.0)
        self.shear_y.set(0.0)
        self.transform_matrix = np.eye(3)

        if self.original_image is not None:
            self.current_image = self.original_image.copy()
            self.reset_view()
            self.update_display()
            self.update_matrix_display()

    def on_mouse_press(self, event):
        """マウスボタンが押されたとき"""
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def on_mouse_drag(self, event):
        """マウスをドラッグしたとき"""
        if self.current_image is None:
            return

        # ドラッグの移動量を計算
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y

        # ビューオフセットを更新
        self.view_offset_x += dx
        self.view_offset_y += dy

        # 次のドラッグの開始点を更新
        self.drag_start_x = event.x
        self.drag_start_y = event.y

        # 表示を更新
        self.update_display()

    def on_mouse_wheel(self, event):
        """マウスホイール/トラックパッド2本指スクロール → ズーム"""
        if self.current_image is None:
            return

        # macOSのトラックパッドでは delta が細かい値で来る
        if event.num == 4 or event.delta > 0:
            zoom_factor = 1.05
        elif event.num == 5 or event.delta < 0:
            zoom_factor = 0.95
        else:
            return

        new_zoom = self.view_zoom * zoom_factor
        if 0.1 <= new_zoom <= 10.0:
            self.view_zoom = new_zoom
            self.update_display()

    def on_ctrl_scroll(self, event):
        """Ctrl+スクロールでもズーム（ブラウザと同じ操作感）"""
        if self.current_image is None:
            return

        if event.delta > 0:
            zoom_factor = 1.15
        elif event.delta < 0:
            zoom_factor = 0.85
        else:
            return

        new_zoom = self.view_zoom * zoom_factor
        if 0.1 <= new_zoom <= 10.0:
            self.view_zoom = new_zoom
            self.update_display()

    def reset_view(self, event=None):
        """ビュー（パン・ズーム）をリセット"""
        self.view_offset_x = 0
        self.view_offset_y = 0
        self.view_zoom = 1.0
        if self.current_image is not None:
            self.update_display()

    def on_magnify(self, event):
        """タッチパッドのピンチイン/アウトジェスチャー"""
        if self.current_image is None:
            return

        # event.delta は拡大率の変化量（正:拡大、負:縮小）
        # macOSではこの値が直接拡大率として使えます
        zoom_factor = 1.0 + event.delta

        # ズームを適用（0.1倍〜10倍の範囲）
        new_zoom = self.view_zoom * zoom_factor
        if 0.1 <= new_zoom <= 10.0:
            self.view_zoom = new_zoom
            self.update_display()

    def on_rotate_gesture(self, event):
        """タッチパッドの回転ジェスチャー（オプション機能）"""
        if self.current_image is None:
            return

        # event.delta は回転角度（度）
        # 現在の回転角度に追加
        current_rotation = self.rotation.get()
        new_rotation = current_rotation + event.delta

        # -180〜180の範囲に正規化
        while new_rotation > 180:
            new_rotation -= 360
        while new_rotation < -180:
            new_rotation += 360

        self.rotation.set(new_rotation)


def main():
    root = tk.Tk()
    app = ImageTransformGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
