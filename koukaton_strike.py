import math
import os
import sys
import pygame as pg

# --- 定数定義 ---
WIDTH = 1100   # ゲームウィンドウの幅
HEIGHT = 650   # ゲームウィンドウの高さ
FPS = 50       # フレームレート

# カラー定義
COLOR_WHITE = (255, 255, 255)
COLOR_RED = (255, 0, 0)
COLOR_BLUE = (0, 0, 255)
COLOR_GREEN = (0, 255, 0)
COLOR_YELLOW = (255, 255, 0)

# カレントディレクトリをスクリプトの場所に合わせる
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct: pg.Rect) -> tuple[int, int]:
    """
    オブジェクトが画面の壁に衝突しているかを判定し、反射係数を返す関数
    """
    yoko, tate = 1, 1
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = -1
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = -1
    return yoko, tate


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    def __init__(self, num: int, xy: tuple[int, int], name: str):
        super().__init__()
        self.name = name  # 識別用の名前
        self.base_img = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 1.2)
        self.image = self.base_img
        self.rect = self.image.get_rect(center=xy)

        # 移動・物理パラメータ
        self.vx = 0.0
        self.vy = 0.0
        self.friction = 0.98

        # ドラッグ・発射管理
        self.is_dragging = False
        self.max_drag_dist = 200  
        self.has_shot = False  # このターンで既に発射されたかどうかのフラグ

    def update(self, screen: pg.Surface, is_my_turn: bool):
        """
        こうかとんの移動、壁での跳ね返り、およびガイドライン・ターン目印の描画
        """
        if not self.is_dragging:
            # 移動処理
            self.rect.move_ip(self.vx, self.vy)

            # 壁との衝突・めり込み防止処理
            yoko, tate = check_bound(self.rect)
            if yoko == -1:
                self.vx *= -1
                self.rect.left = max(0, self.rect.left)
                self.rect.right = min(WIDTH, self.rect.right)
            if tate == -1:
                self.vy *= -1
                self.rect.top = max(0, self.rect.top)
                self.rect.bottom = min(HEIGHT, self.rect.bottom)

            # 摩擦による減速
            self.vx *= self.friction
            self.vy *= self.friction
            
            # 完全停止判定
            if math.hypot(self.vx, self.vy) < 0.1:
                self.vx, self.vy = 0.0, 0.0

        # ドラッグ中のガイドライン描画
        if is_my_turn and self.is_dragging:
            mouse_pos = pg.mouse.get_pos()
            dx = mouse_pos[0] - self.rect.centerx
            dy = mouse_pos[1] - self.rect.centery
            dist = math.hypot(dx, dy)
            
            if dist > self.max_drag_dist:
                dx = (dx / dist) * self.max_drag_dist
                dy = (dy / dist) * self.max_drag_dist
            
            # 引っ張る方向とは逆（飛んでいく方向）への赤い矢印（線）
            target_x = self.rect.centerx - dx
            target_y = self.rect.centery - dy
            pg.draw.line(screen, COLOR_RED, self.rect.center, (target_x, target_y), 5)
            
            # マウスで引っ張っている方向への青い線と丸
            current_drag_x = self.rect.centerx + dx
            current_drag_y = self.rect.centery + dy
            pg.draw.line(screen, COLOR_BLUE, self.rect.center, (current_drag_x, current_drag_y), 2)
            pg.draw.circle(screen, COLOR_BLUE, (int(current_drag_x), int(current_drag_y)), 8)

        # キャラクターの描画
        screen.blit(self.image, self.rect)

        # 自分のターンであることの目印（足元に黄色い円を描画）
        if is_my_turn:
            pg.draw.circle(screen, COLOR_YELLOW, self.rect.center, self.rect.width // 2 + 5, 2)


class Enemy(pg.sprite.Sprite):
    """
    敵キャラクター（スライム）に関するクラス
    """
    def __init__(self, xy: tuple[int, int]):
        super().__init__()
        self.image = pg.transform.rotozoom(pg.image.load("fig/suraimu.png"), 0, 0.2)
        self.rect = self.image.get_rect(center=xy)
        
        self.max_hp = 5  
        self.hp = self.max_hp
        #---追加：敵の無敵時間タイマー--- 
        self.muteki_time = 0 #0より大きいときは無敵状態
    def update(self, screen: pg.Surface):
        """
        敵の描画とHPバーの描画を行う
        """
        #---追加：敵の無敵時間タイマー---
        if self.muteki_time > 0:
            self.muteki_time -= 1

        screen.blit(self.image, self.rect)

        # HPバーの描画
        if self.hp > 0:
            bar_width = 30  
            bar_height = 5
            bar_x = self.rect.centerx - bar_width // 2
            bar_y = self.rect.top - 8  
            
            # 背景（赤）
            pg.draw.rect(screen, COLOR_RED, (bar_x, bar_y, bar_width, bar_height))
            # 残りHP（緑）
            hp_ratio = self.hp / self.max_hp
            pg.draw.rect(screen, COLOR_GREEN, (bar_x, bar_y, int(bar_width * hp_ratio), bar_height))



class HitEffect(pg.sprite.Sprite):
    """
    衝突時に一瞬だけ表示されるエフェクト
    """

    def __init__(self, xy: tuple[int,int]):
        super().__init__()
        a_image = pg.image.load("fig/hit.png")
        self.image = pg.transform.rotozoom(a_image, 0, 0.2)
        self.rect = self.image.get_rect()
        self.rect.center = xy

        self.lifetime = 10 #ほかのエフェクトに被るようならここを変更

    def update(self, screen: pg.Surface):
        """
        エフェクトを表示し、寿命が来たら自身を削除する
        """
        if self.lifetime > 0:
            screen.blit(self.image, self.rect)
            self.lifetime -= 1
        else:
            self.kill()

def main():
    pg.display.set_caption("こうかとんストライク（2人交互ターン制）")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load("fig/senjou.png")
    font = pg.font.SysFont("hgp創英角ﾎﾟｯﾌﾟ体", 30)

    # BGMの設定と再生
    pg.mixer.music.load("bgm.mp3")            
    pg.mixer.music.play(loops=-1)            

    # プレイヤー（こうかとん）の初期化
    birds = [
        Bird(3, (WIDTH // 4, HEIGHT // 3), "プレイヤー1"),   
        Bird(1, (WIDTH // 4, HEIGHT * 2 // 3), "プレイヤー2") 
    ]
    turn_idx = 0  # 現在のターンインデックス
    
    # 敵グループの初期化
    enemies = pg.sprite.Group()
    enemy = Enemy((WIDTH * 3 // 4, HEIGHT // 4))
    enemies.add(enemy)

    #---追加: エフェクトのグループ---
    effects = pg.sprite.Group()

    clock = pg.time.Clock()
   
    while True:
        current_bird = birds[turn_idx]  # 現在のターンのこうかとん
        
        # --- イベント処理 ---
        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg.mixer.music.stop()
                return 0
            
            # マウスダウン: 引っぱりの開始
            if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                if current_bird.rect.collidepoint(event.pos) and not current_bird.has_shot:
                    current_bird.is_dragging = True
                    current_bird.vx, current_bird.vy = 0.0, 0.0

            # マウスアップ: 発射
            if event.type == pg.MOUSEBUTTONUP and event.button == 1:
                if current_bird.is_dragging:
                    current_bird.is_dragging = False
                    current_bird.has_shot = True  
                    
                    mouse_pos = event.pos
                    dx = mouse_pos[0] - current_bird.rect.centerx
                    dy = mouse_pos[1] - current_bird.rect.centery
                    dist = math.hypot(dx, dy)
                    
                    if dist > current_bird.max_drag_dist:
                        dx = (dx / dist) * current_bird.max_drag_dist
                        dy = (dy / dist) * current_bird.max_drag_dist
                    
                    # ひっぱった方向の逆へ飛ばす（速度係数 0.25）
                    current_bird.vx = -dx * 0.25
                    current_bird.vy = -dy * 0.25

        # --- ターン切り替えロジック ---
        # 発射済み、かつ完全に静止したら次のプレイヤーへ
        if current_bird.has_shot and current_bird.vx == 0.0 and current_bird.vy == 0.0:
            current_bird.has_shot = False  
            turn_idx = (turn_idx + 1) % len(birds)  

        # --- 衝突判定の処理 ---
        for bird in birds:
            # 動いていない時は衝突判定をスキップして多重ヒットを防ぐ
            if bird.vx == 0.0 and bird.vy == 0.0:
                continue

            for en in enemies:
                if bird.rect.colliderect(en.rect):
                    #---追加：敵の無敵時間タイマー---
                    if en.muteki_time == 0:
                        en.hp -= 1
                        en.muteki_time = 25

                        new_effect = HitEffect(en.rect.center)
                        effects.add(new_effect)
                    bird.rect.move_ip(-bird.vx, -bird.vy)
                    # 跳ね返り処理（めり込み防止のため少し減速して反転）
                    if math.hypot(bird.vx, bird.vy) > 0.5:
                        bird.vx *= -0.5
                        bird.vy *= -0.5
                    
                    # 敵の死亡判定
                    if en.hp <= 0:
                        en.kill()

        # --- 描画処理 ---
        screen.blit(bg_img, [0, 0])
        
        # こうかとんの更新と描画
        for i, bird in enumerate(birds):
            bird.update(screen, is_my_turn=(i == turn_idx))
            
        # 敵の更新と描画
        enemies.update(screen)

        # 追加: エフェクトの更新と描画 
        effects.update(screen)
        
        # 画面上部に現在のターンを表示
        turn_text = font.render(f"現在のターン: {birds[turn_idx].name}", True, COLOR_WHITE)
        screen.blit(turn_text, (20, 20))
        
        pg.display.update()
        clock.tick(FPS)


if __name__ == "__main__":
    pg.init()
    pg.mixer.init()
    main()
    pg.quit()
    sys.exit()