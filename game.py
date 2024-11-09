import os
import sys
import pygame as pg
import math
import random
import csv
import time

pg.init()
pg.mixer.pre_init()
pg.mixer.init()

music_volume = 0.2
sfx_volume = 0.5
bg_music = pg.mixer.Sound('assets/04 - Disco Descent (1-1).mp3')
bg_music.set_volume(music_volume)

over_music = pg.mixer.Sound('assets/over.mp3')
over_music.set_volume(music_volume)

empty_mag = pg.mixer.Sound('assets/empty-magazine.wav')
empty_mag.set_volume(sfx_volume)

wall_hit = pg.mixer.Sound('assets/bullet-hit-concrete.wav')
wall_hit.set_volume(sfx_volume*0.5)

# prediction for aim bot
def prediction(proj_pos, proj_speed, target_pos, target_vel):
    d_x = target_pos.x - proj_pos.x
    d_y = target_pos.y - proj_pos.y

    a = target_vel.x**2 + target_vel.y**2 - proj_speed**2
    b = 2 * (target_vel.x * d_x + target_vel.y * d_y)
    c = d_x**2 + d_y**2

    ts = quad(a,b,c)

    pos2aim = target_pos
    if ts:
        t = min(ts[0],ts[1])
        if t < 0:
            t = max(ts[0],ts[1])
        if t > 0:
            pos2aim = (target_pos.x + target_vel.x * t, \
                       target_pos.y + target_vel.y * t)
    return pos2aim
def quad(a,b,c):
    sol = None
    if a == 0:
        if b == 0:
            if c == 0:
                sol = (0,0)
            else:
                sol = None
        else:
            sol = (-c/b, -c/b)
    else:
        delta = b*b - 4*a*c
        if delta >= 0:
            delta = math.sqrt(delta)
            two_a = 2*a
            sol = ((-b-delta)/two_a, (-b+delta)/two_a)
    return sol

#rorate center
def rot_center(image, angle, x, y):
    rotated_image = pg.transform.rotate(image, angle)
    new_rect = rotated_image.get_rect(center = image.get_rect(center = (x, y)).center)
    return rotated_image, new_rect
def to_angle(point1,point2):
    angle = math.degrees(math.atan2(-(point2[1] - point1[1]),(point2[0] - point1[0])))
    return angle
def rotate_vector(vector, angle):
    x = vector.x * math.cos(angle) - vector.y * math.sin(angle)
    y = vector.x * math.sin(angle) + vector.y * math.cos(angle)
    return pg.math.Vector2(x, y)

def load_map(level_num):
    filename = f"map{level_num}.csv"
    with open(filename, newline='') as csvfile:
        map_reader = csv.reader(csvfile, delimiter=',')
        return [list(map(int, row)) for row in map_reader]

def get_random_point_around(pos, r1, r2):
    # Random distance within the radius range
    distance = random.uniform(r1, r2)
    # Random angle between 0 and 2π (full circle in radians)
    angle = random.uniform(0, 2 * math.pi)
    
    # Calculate the offset based on polar coordinates
    offset_x = distance * math.cos(angle)
    offset_y = distance * math.sin(angle)
    
    # New position by adding the offset to the original position
    new_x = pos[0] + offset_x
    new_y = pos[1] + offset_y
    
    return (int(new_x), int(new_y))

def distance(p1,p2):
    return math.hypot(p2[0]-p1[0],p2[1]-p1[1])

def path_blocked(p1, p2,block_list):
    #check if the path from 1 point to another is blocked
    src = pg.Vector2(p1[0],p1[1])
    dest = pg.Vector2(p2[0],p2[1])
    for block in block_list:
        if block.rect.collidepoint(src.x,src.y):
            return True
    while True:
        src.move_towards_ip(dest,10)
        for block in block_list:
            if block.rect.collidepoint(src.x,src.y):
                return True

        if src == dest:
            return False


class UI:
    def __init__(self):
        self.smallest_font = pg.font.SysFont("arial",12,True) #bad way to make font
        self.small_font = pg.font.SysFont("arial",18,True)
        self.font = pg.font.SysFont("arial",28,True)
        self.big_font = pg.font.SysFont("arial",38,True)
        self.hp_bar = pg.Rect(0,0,50,10)
        self.reloading_bar = pg.Rect(0,0,50,5)
        self.ui_bg_color = "gray"
        self.hp_color = "#00CC00"
        self.reload_color = "#808080"
        self.mouse = (0,0)
    def show_hp_bar(self,screen,enti_list,offset):
        for enti in enti_list:
            self.hp_bar.centerx = enti.pos.x -offset[0]
            self.hp_bar.bottom = enti.pos.y-offset[1] - (10+enti.r)

            current = enti.hp
            max_amount = enti.max_hp

            ratio = current / max_amount
            current_w = self.hp_bar.width * ratio
            current_hp_rect = self.hp_bar.copy()
            current_hp_rect.width = current_w

            pg.draw.rect(screen,self.ui_bg_color,self.hp_bar)
            pg.draw.rect(screen, self.hp_color, current_hp_rect)
    def show_reload(self,screen,enti_list,offset):
        for enti in enti_list:
            if enti.reloading:
                self.reloading_bar.top = enti.pos.y-offset[1] + 30
                self.reloading_bar.centerx = enti.pos.x-offset[0]
                elapsed = pg.time.get_ticks()-enti.reload_start
                reloadtime = enti.using_weapon.reload_time
                if elapsed < reloadtime:
                    ratio = elapsed / reloadtime
                    current_w = self.reloading_bar.width * ratio
                    current_rect = self.reloading_bar.copy()
                    current_rect.width = current_w

                    pg.draw.rect(screen,self.ui_bg_color,self.reloading_bar)
                    pg.draw.rect(screen, self.reload_color, current_rect)
    def show_ammo(self,screen,enti_list,offset):
        for enti in enti_list:
            if enti.ammo[enti.weapon_index] > 0:
                self.render_text(screen,self.small_font,enti.ammo[enti.weapon_index],(enti.pos.x+enti.r+10-offset[0],enti.pos.y+10-offset[1]),"black")
            elif not enti.reloading:
                self.render_text(screen,self.smallest_font,"OUT OF AMMO!",(enti.pos.x-offset[0],enti.pos.y+enti.r+10-offset[1]),"red")
    def show_debug(self,screen,enti_list,offset):
        pass
    def show_kills(self,screen,kills):
        txt_surf = self.font.render(f'KILLS: {kills}',True,"black")
        text_rect = txt_surf.get_rect(topleft=(0,0))
        screen.blit(txt_surf,text_rect)
    def render_text(self,screen,font, text, pos, color):
        txt_surf = font.render(str(text),True,color)
        text_rect = txt_surf.get_rect(center=(pos[0],pos[1]))
        screen.blit(txt_surf,text_rect)
    def display_title_screen(self,screen):
        self.render_text(screen,self.font,"Press any button to start!!",(screen.get_width()/2,screen.get_height()/2),"black") 
class Bullet(pg.sprite.Sprite):
    def __init__(self,shooter,direction,speed,dmg,r,pierce=False):
        super().__init__()
        self.shooter = shooter
        self.speed = speed
        self.dmg = dmg
        self.r = r
        self.pierce = pierce
        self.predicted = False
        self.direction = direction.normalize()
        self.lifetime = 3000
        self.created_time = pg.time.get_ticks()
        self.pos = pg.Vector2(shooter.pos[0]+self.direction[0]*shooter.r, shooter.pos[1]+self.direction[1]*shooter.r+self.shooter.shoot_height)
        self.color = "#FB4700"
    def move(self,dt):
        self.pos[0] += self.direction.x * self.speed * dt
        self.pos[1] += self.direction.y * self.speed * dt
    
    def draw(self,screen,offset):
        pg.draw.circle(screen,self.color,(round(self.pos.x-offset[0]), round(self.pos.y-offset[1])),self.r)

    def update(self,dt):
        self.move(dt)
        if pg.time.get_ticks() - self.created_time > self.lifetime:
            self.kill()

class Rifle:
    proj_speed = 25
    dmg = 30
    cooldown = 100
    reload_time = 1700
    spread = 1
    max_ammo = 30
    ammo_radius = 4
    recoil = 4
    shots = 1
    vision = 400
    image = pg.transform.scale(pg.image.load('assets/pngegg.png'),(80,40))
    shoot_sound = pg.mixer.Sound('assets/ak47-shot.wav')
    shoot_sound.set_volume(sfx_volume)
    reload_sound = pg.mixer.Sound('assets/ak47-reload.wav')
    reload_sound.set_volume(sfx_volume)

class Shotgun:
    proj_speed = 20
    dmg = 20
    cooldown = 600
    reload_time = 3000
    spread = 5
    max_ammo = 8
    ammo_radius = 4
    recoil = 18
    shots = 11
    vision = 300
    image = pg.transform.scale(pg.image.load('assets/shotgun.png'),(80,40))
    shoot_sound = pg.mixer.Sound('assets/shotgun-shot.wav')
    shoot_sound.set_volume(sfx_volume*1.5)
    reload_sound = pg.mixer.Sound('assets/shotgun-reload.wav')
    reload_sound.set_volume(sfx_volume)

class Sniper:
    proj_speed = 35
    dmg = 180
    cooldown = 1000
    reload_time = 3000
    spread = 0
    max_ammo = 5
    ammo_radius = 4
    recoil = 0
    shots = 1
    vision = 600
    image = pg.transform.scale(pg.image.load('assets/m1_garand_by_tharn666_deedqmz.png'),(80,50))
    shoot_sound = pg.mixer.Sound('assets/sniper-shot.wav')
    shoot_sound.set_volume(sfx_volume*1.5)
    reload_sound = pg.mixer.Sound('assets/sniper-reload.wav')
    reload_sound.set_volume(sfx_volume)
    eject_sound = pg.mixer.Sound('assets\ping_4TjeI1U.mp3')
    eject_sound.set_volume(sfx_volume*1.5)

class HealthKit:
    def __init__(self,pos):
        self.image = pg.image.load('assets/hp-kit.png').convert_alpha()
        self.image = pg.transform.scale(self.image,(30,30))
        self.rect = self.image.get_rect(topleft = pos)
        self.width = self.rect.width
        self.height = self.rect.height
        self.pos = pg.Vector2(self.rect.topleft)
        self.heal = 80
    def draw(self,screen,offset):
        screen.blit(self.image,
                    (round(self.pos.x-offset[0]), round(self.pos.y-offset[1]),30,30)
                    )

class Entity(pg.sprite.Sprite):
    def __init__(self,game,x,y,r,lives,color,speed,weapons=None):
        super().__init__()
        self.game = game
        self.max_hp = 300
        self.hp = 300
        self.color = color
        self.pos = pg.Vector2(x, y)
        self.r = r
        self.speed = speed
        self.weapons = weapons if weapons is not None else [random.choice([Rifle,Shotgun,Sniper])]
        self.weapon_index = 0
        self.using_weapon = self.weapons[self.weapon_index]
        self.shoot_height = 5
        self.reloading = False
        self.lives = lives
        self.vision = 5
        self.kills = 0
        self.elites = [random.random()>0.5,random.random()>0.8,random.random()>0.8] # follow,dodge,auto_aim
        self.direction = pg.math.Vector2()
        self.lastshoot = 0
        self.reload_start = 0
        self.ammo = [i.max_ammo for i in self.weapons]
        self.ai_controlling = False
        self.dest = (0,0)
        self.moving_chance = 30
        self.last_hit_by = None
        self.aim = pg.Vector2(1,1)
    def shoot(self,target):
        if self.elites[2] and self != self.game.playing_player:
            target = prediction(self.pos,self.using_weapon.proj_speed,pg.Vector2(target),self.game.playing_player.direction * self.game.playing_player.speed)
        self.aim.update(target[0],target[1])
        currenttime = pg.time.get_ticks()
        if currenttime - self.lastshoot > self.using_weapon.cooldown:
            if self.ammo[self.weapon_index] > 0:
                self.using_weapon.shoot_sound.play()
                direction = pg.math.Vector2((target[0] - self.pos.x),\
                                            (target[1] - self.pos.y))
                self.knockback(-direction.normalize(),self.using_weapon.recoil) 
                for _ in range(self.using_weapon.shots):
                    rotated_dir = direction.rotate(random.uniform(-self.using_weapon.spread,self.using_weapon.spread))
                    self.game.proj_list.append(Bullet(self,rotated_dir,self.using_weapon.proj_speed,self.using_weapon.dmg,self.using_weapon.ammo_radius,self.using_weapon==Sniper))
                self.lastshoot = currenttime 
                self.ammo[self.weapon_index] -= 1
                if self.using_weapon == Sniper and self.ammo[self.weapon_index] == 0:
                    Sniper.eject_sound.play()
                
            else:
                empty_mag.play()
                self.lastshoot = currenttime 
    def start_reload(self):
        if not self.reloading:
            self.using_weapon.reload_sound.play()
            self.reloading = True
            self.reload_start = pg.time.get_ticks()
    def reload(self):
        if self.reloading and pg.time.get_ticks() - self.reload_start > self.using_weapon.reload_time:
            self.ammo[self.weapon_index] = self.using_weapon.max_ammo
            self.reloading = False
    def switch_weapon(self,num):
        self.weapon_index = num
        self.using_weapon = self.weapons[num]
        self.reloading = False
        if self.using_weapon == Sniper:
            self.speed = 2
            self.vision = 2
        elif self.using_weapon == Shotgun:
            self.speed = 4
            self.vision = 10
        else:
            self.speed = 5
            self.vision = 5
        
    def decrease_hp(self,amount):
        if self.using_weapon == Shotgun:
            amount *= 0.6
            amount = min(50,amount)
        self.hp = max(self.hp - amount,0)
    def increase_hp(self,amount):
        self.hp = min(self.hp + amount,self.max_hp) 
    def move(self,dt):
        self.pos[0] += self.direction.x * self.speed * dt
        self.pos[1] += self.direction.y * self.speed * dt
    def knockback(self,direction,amount):
        self.pos[0] += direction[0] * amount
        self.pos[1] += direction[1] * amount
    
    def draw(self,screen,offset=(0,0)):
        pg.draw.circle(screen,self.color,(round(self.pos.x-offset[0]), round(self.pos.y-offset[1])),self.r)
        if self.aim.x < self.pos.x:
            w_img = pg.transform.rotate(pg.transform.flip(self.using_weapon.image,False,True),
                                                to_angle((self.pos.x,self.pos.y+self.shoot_height),(self.aim.x,self.aim.y)))
        else:
            w_img = pg.transform.rotate(self.using_weapon.image,
                                                to_angle((self.pos.x,self.pos.y+self.shoot_height),(self.aim.x,self.aim.y)))
        screen.blit(w_img,w_img.get_rect(center = (round(self.pos.x-offset[0]), round(self.pos.y-offset[1]+self.shoot_height+5))))
    def update(self,dt):
        self.move(dt)
        self.reload()
        

class Tile(pg.sprite.Sprite):
    def __init__(self,x,y,width,height):
        self.pos = pg.Vector2(x,y)
        self.image = pg.Surface((width,height))
        self.rect = self.image.get_rect(topleft=(x,y))
        self.width = self.rect.width
        self.height = self.rect.height
    def draw(self,screen,offset):
        pg.draw.rect(screen,"#333333",(self.pos[0]-offset[0],self.pos[1]-offset[1],self.width,self.height))

class BotAI:
    def __init__(self,game):
        self.game = game
    def set_direction(self,enti:Entity):
        enti.direction.update(enti.dest[0]-enti.pos.x,enti.dest[1]-enti.pos.y)
        enti.direction.normalize_ip()
    def stop_direction(self,enti):
        enti.dest = (0,0)
        enti.direction.update(0,0)
    def get_random_dest(self,enti):
        if enti.elites[0]:# get dest closet to player
            dests = [get_random_point_around(enti.pos,200,400) for _ in range(10)]
            dests = [p for p in dests if not path_blocked(enti.pos,p,self.game.block_list)]
            if len(dests) > 0:
                dests.sort(key=lambda d: distance(self.game.playing_player.pos,d))
                enti.dest = dests[0]
                return
        
        dest = get_random_point_around(enti.pos,40,400)
        if path_blocked(enti.pos,dest,self.game.block_list):
            return
        enti.dest = dest
    def control_bots(self):
        for enti in self.game.enti_list:
            if enti == self.game.playing_player:
                continue
            if enti.dest == (0,0):
                if random.randrange(0,100) < enti.moving_chance:
                    self.get_random_dest(enti)
            else:
                if enti.pos.distance_to(enti.dest) < enti.r+3:
                    self.stop_direction(enti)
                else:
                    self.set_direction(enti)
            if not path_blocked(enti.pos,self.game.playing_player.pos,self.game.block_list) and distance(enti.pos,self.game.playing_player.pos) < enti.using_weapon.vision:
                enti.shoot(self.game.playing_player.pos)
            if enti.ammo[enti.weapon_index] < 1:
                enti.start_reload()
            
                

class Game:
    def __init__(self,screen:pg.Surface,fps,ui:UI,mapnum):
        self.tile_size = 40
        self.map = None
        self.screen = screen
        self.screen_w = screen.get_width()
        self.screen_h = screen.get_height()
        self.pause_bg = pg.Surface((self.screen_w,self.screen_h))
        self.pause_bg.set_alpha(220)
        self.pause_bg.fill("black")
        self.fps = fps
        self.ui = ui
        self.isPlaying = True
        self.enti_list = []
        self.block_list = []
        self.proj_list = []
        self.item_list = []
        self.playing_player = None
        self.scroll = pg.Vector2()
        self.botAI = BotAI(self)
        self.spawn_points = []
        self.spawn_duration = 5000
        self.last_spawn = 0
        self.over_music_played = False
        self.init_map(mapnum)
    def init_map(self,mapnum):
        self.map = load_map(mapnum)
        spawn_positions = []
        for row_idx, row in enumerate(self.map):
            for col_idx, tile in enumerate(row):
                if tile == 0: 
                    spawn_positions.append((col_idx, row_idx))
                if tile == 1:
                    self.block_list.append(Tile(col_idx*self.tile_size,row_idx*self.tile_size,self.tile_size,self.tile_size))
        
        self.spawn_points = spawn_positions.copy()
        player_spawn_point = random.choice(spawn_positions)
        self.playing_player = Entity(self, (player_spawn_point[0]+0.5)*self.tile_size, (player_spawn_point[1]+0.5)*self.tile_size,20,3,"#EE1100",5,[Rifle,Shotgun,Sniper])
        self.enti_list.append(self.playing_player)
        spawn_positions.remove(player_spawn_point)

        spawn_positions = [p for p in spawn_positions if distance(self.playing_player.pos,(p[0]*self.tile_size,p[1]*self.tile_size))>400]
        for _ in range(random.randrange(1,3)):
            spawnpoint = random.choice(spawn_positions)
            self.enti_list.append(Entity(self,(spawnpoint[0]+0.5)*self.tile_size,(spawnpoint[1]+0.5)*self.tile_size,20,3,"blue",2))
            spawn_positions.remove(spawnpoint)

    def collision_enti_enti(self):
        for i in range(len(self.enti_list)):
            enti_1 = self.enti_list[i]
            for j in range(i+1,len(self.enti_list)):
                enti_2 = self.enti_list[j]
                dist = max(pg.Vector2.distance_to(enti_1.pos, enti_2.pos),1)
                min_dist = enti_1.r + enti_2.r
                # print(min_dist)
                if dist < min_dist:
                    collision_axis = enti_1.pos - enti_2.pos
                    direction = collision_axis/dist #same as collicsion_axis.normalize
                    delta = min_dist-dist
                    enti_1.pos += 0.5 * delta * direction
                    enti_2.pos -= 0.5 * delta * direction
    
    def collision_enti_block(self):
        for enti in self.enti_list:
            for block in self.block_list:
                # Find the closest point on the rectangle to the circle's center
                closest_x = max(block.pos[0], min(enti.pos[0], block.pos[0] + block.width))
                closest_y = max(block.pos[1], min(enti.pos[1], block.pos[1] + block.height))

                # Calculate the distance between the circle's center and this closest point
                distance_x = enti.pos[0] - closest_x
                distance_y = enti.pos[1] - closest_y
                distance = math.sqrt(distance_x ** 2 + distance_y ** 2)

                # Check for collision (distance <= radius)
                if distance < enti.r:
                    # Determine which side of the rectangle the circle hit
                    if closest_x == block.pos[0] or closest_x == block.pos[0] + block.width:
                        # Collision on the left or right
                        enti.direction.x = -enti.direction.x
                    if closest_y == block.pos[1] or closest_x == block.pos[1] + block.height:
                        # Collision on the top or bottom
                        enti.direction.y = -enti.direction.y

                    # Move the circle out of collision
                    overlap = enti.r - distance
                    if distance != 0:  # Prevent division by zero
                        enti.pos[0] += (distance_x / distance) * overlap
                        enti.pos[1] += (distance_y / distance) * overlap

    def collision_proj_enti(self):
        for proj in self.proj_list.copy():
            for enti in self.enti_list:
                if proj.shooter == enti:
                    continue
                dist = proj.pos.distance_to(enti.pos)
                min_dist = proj.r + enti.r
                if dist < min_dist:
                    enti.decrease_hp(proj.dmg)
                    if proj.shooter.using_weapon == Rifle:
                        proj.shooter.increase_hp(proj.dmg*0.25) 
                    enti.last_hit_by = proj.shooter
                    self.proj_list.remove(proj)
                    break

    def collision_proj_block(self):
        for proj in self.proj_list:
            for block in self.block_list:
                closest_x = max(block.pos[0], min(proj.pos[0], block.pos[0] + block.width))
                closest_y = max(block.pos[1], min(proj.pos[1], block.pos[1] + block.height))

                distance_x = proj.pos[0] - closest_x
                distance_y = proj.pos[1] - closest_y
                dist = math.sqrt(distance_x ** 2 + distance_y ** 2)

                if dist < proj.r:
                    vol = 1 - min(distance(proj.pos,self.playing_player.pos)/400,1)
                    wall_hit.set_volume(vol*0.6)
                    wall_hit.play()
                    if not proj.pierce:
                        self.proj_list.remove(proj)
                    else:
                        proj.pierce = (random.random() < 0.85)
                    break


    
    def collision_enti_item(self):
        for enti in self.enti_list:
            for item in self.item_list:
                closest_x = max(item.pos[0], min(enti.pos[0], item.pos[0] + item.width))
                closest_y = max(item.pos[1], min(enti.pos[1], item.pos[1] + item.height))
                distance_x = enti.pos[0] - closest_x
                distance_y = enti.pos[1] - closest_y
                distance = math.sqrt(distance_x ** 2 + distance_y ** 2)

                if distance < enti.r:
                    enti.increase_hp(item.heal)
                    self.item_list.remove(item)
                
    def spawn_something(self):
        spawnpoint = random.choice(self.spawn_points)
        x = (spawnpoint[0]+0.5)*self.tile_size
        y = (spawnpoint[1]+0.5)*self.tile_size
        if distance((x,y),self.playing_player.pos) < 400:
            return
        if pg.time.get_ticks() - self.last_spawn > self.spawn_duration:
            if random.choice([1,2,3]) == 1  and len(self.enti_list) < 5:
                self.enti_list.append(Entity(self,x,y,20,3,"blue",2))
            else:
                spawnpoint = random.choice(self.spawn_points)
                self.item_list.append(HealthKit(((spawnpoint[0])*self.tile_size,(spawnpoint[1])*self.tile_size)))
            self.last_spawn = pg.time.get_ticks()
        if len(self.enti_list) < 2:
            self.enti_list.append(Entity(self,x,y,20,3,"blue",2))
    def handle_inputs(self):
        #get keys
        keys = pg.key.get_pressed()
        if keys[pg.K_a]:
            self.playing_player.direction.x = -1
        elif keys[pg.K_d]:
            self.playing_player.direction.x = 1
        else:
            self.playing_player.direction.x = 0
        # vertical
        if keys[pg.K_w]:
            self.playing_player.direction.y = -1
        elif keys[pg.K_s]:
            self.playing_player.direction.y = 1
        else:
            self.playing_player.direction.y = 0

        if abs(self.playing_player.direction.x) == 1 and abs(self.playing_player.direction.y) == 1:
            self.playing_player.direction = self.playing_player.direction.normalize()
        
        if keys[pg.K_1]:
            self.playing_player.switch_weapon(0)
        elif keys[pg.K_2]:
            self.playing_player.switch_weapon(1)
        elif keys[pg.K_3]:
            self.playing_player.switch_weapon(2)

        if keys[pg.K_r]:
            self.playing_player.start_reload()
        #get mouse

        mouse = pg.mouse.get_pressed()
        aim = pg.mouse.get_pos()
        aim = (int(aim[0]+self.scroll[0]),int(aim[1]+self.scroll[1]))
        self.playing_player.aim.update(aim)
        if mouse[0] and not self.playing_player.reloading:
            self.playing_player.shoot(aim)
    def render(self):
        self.screen.fill("white")

        self.scroll[0] += (self.playing_player.pos.x - self.screen_w/2 - self.scroll[0] + (self.playing_player.aim.x-self.playing_player.pos.x)/self.playing_player.vision)/20
        self.scroll[1] += (self.playing_player.pos.y - self.screen_h/2 - self.scroll[1] + (self.playing_player.aim.y-self.playing_player.pos.y)/self.playing_player.vision)/20
        for item in self.item_list:
            item.draw(self.screen,self.scroll)
        for enti in self.enti_list:
            enti.draw(self.screen,self.scroll)
        for block in self.block_list:
            block.draw(self.screen,self.scroll)
        for proj in self.proj_list:
            proj.draw(self.screen,self.scroll)
        
        if self.playing_player.using_weapon == Sniper:
            pg.draw.line(self.screen,"green",
                         (self.playing_player.pos-self.scroll+pg.Vector2(0,5)).move_towards(self.playing_player.aim-self.scroll,40),
                         self.playing_player.aim-self.scroll,2)

        self.ui.show_hp_bar(self.screen,self.enti_list,self.scroll)
        self.ui.show_reload(self.screen,self.enti_list,self.scroll)
        self.ui.show_ammo(self.screen,self.enti_list,self.scroll)
        self.ui.show_debug(self.screen,self.enti_list,self.scroll)
        self.ui.show_kills(screen,self.playing_player.kills)
    def update(self,dt):
        self.handle_inputs()
        for enti in self.enti_list:
            enti.update(dt)
            if enti != self.playing_player and enti.hp < 1:
                enti.last_hit_by.kills += 1
                self.enti_list.remove(enti)
        for proj in self.proj_list:
            proj.update(dt)
        self.collision_enti_enti()
        self.collision_enti_block()
        self.collision_proj_enti()
        self.collision_proj_block()
        self.collision_enti_item()
        self.spawn_something()
        self.botAI.control_bots()
    def pause_screen(self):
        self.isPlaying = not self.isPlaying
        self.screen.blit(self.pause_bg,(0,0))
        self.ui.render_text(self.screen,self.ui.big_font,"PAUSED",(self.screen_w/2,self.screen_h/4),"white")
        self.ui.render_text(self.screen,self.ui.font,"Left Mouse: Shoot",(self.screen_w/2,self.screen_h/2),"white")
        self.ui.render_text(self.screen,self.ui.font,"R: Reload",(self.screen_w/2,self.screen_h/2 + 28),"white")
        self.ui.render_text(self.screen,self.ui.font,"ESC: Continue",(self.screen_w/2,self.screen_h/2 + 28*2),"white")
        self.ui.render_text(self.screen,self.ui.font,"1,2,3: Change weapon",(self.screen_w/2,self.screen_h/2 + 28*3),"white")
        self.ui.render_text(self.screen,self.ui.font,"Q: Quit",(self.screen_w/2,self.screen_h/2 + 28*4),"white")
    def over_screen(self):
        self.screen.blit(pg.Surface((self.screen_w,self.screen_h)),(0,0))
        self.ui.render_text(self.screen,self.ui.big_font,"GAME OVER",(self.screen_w/2,self.screen_h/4),"white")
        self.ui.render_text(self.screen,self.ui.font,f"Kills: {self.playing_player.kills}",(self.screen_w/2,self.screen_h/2 + 28),"white")
        self.ui.render_text(self.screen,self.ui.font,"Q: Back to title screen",(self.screen_w/2,self.screen_h/2 + 28*3),"white")

    def mainloop(self):
        prevtime = time.time()
        while True:
            dt = time.time() - prevtime
            prevtime = time.time()
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    pg.quit()
                    sys.exit()
                if event.type == pg.KEYDOWN :
                    if event.key == pg.K_ESCAPE and self.playing_player.hp > 1:
                        self.pause_screen()
                    if event.key == pg.K_q and not self.isPlaying:
                        bg_music.stop()
                        over_music.stop()
                        return

            if self.playing_player.hp < 1:
                self.over_screen()
                bg_music.stop()
                if not self.over_music_played:
                    self.over_music_played = True
                    over_music.play()
                self.isPlaying = False
            
            if self.isPlaying:
                self.render()
                self.update(dt*60)

            pg.display.update()



if __name__ == "__main__":
    FPS = 60
    SCREEN_W,SCREEN_H = 1000,700
    screen = pg.display.set_mode((SCREEN_W,SCREEN_H))
    running = True
    isIngame = False
    ui = UI()
    clock = pg.time.Clock()
    while running:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
                pg.quit()
                sys.exit()
            if event.type == pg.KEYDOWN:
                bg_music.play(-1,0)
                game = Game(screen,FPS,ui,random.choice([1,2,3]))
                game.mainloop()

        screen.fill("#6a6aad")
        ui.display_title_screen(screen)
        pg.display.update()
        clock.tick(FPS)

        
