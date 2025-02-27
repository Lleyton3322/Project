import pygame


class InventoryItem:
    def __init__(self, item_id, name, description, value, weight, category, icon=None):
        self.item_id = item_id
        self.name = name
        self.description = description
        self.value = value
        self.weight = weight
        self.category = category
        self.icon = icon or self._create_default_icon()
        self.quantity = 1

    def _create_default_icon(self):
        icon = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.rect(icon, (150, 150, 150), (0, 0, 32, 32))
        return icon


class EnhancedInventory:
    def __init__(self, capacity=100.0):
        self.items = []
        self.max_capacity = capacity
        self.current_weight = 0.0
        self.selected_item = None
        self.drag_offset = None

    def add_item(self, item):
        if self.current_weight + item.weight > self.max_capacity:
            return False

        for inv_item in self.items:
            if inv_item.item_id == item.item_id:
                inv_item.quantity += item.quantity
                self.current_weight += item.weight
                return True

        self.items.append(item)
        self.current_weight += item.weight
        return True

    def remove_item(self, item):
        if item in self.items:
            self.items.remove(item)
            self.current_weight -= (item.weight * item.quantity)
            return True
        return False

    def start_drag(self, mouse_pos, item):
        self.selected_item = item
        self.drag_offset = (mouse_pos[0] - item.icon.get_rect().x,
                            mouse_pos[1] - item.icon.get_rect().y)

    def end_drag(self, mouse_pos):
        self.selected_item = None
        self.drag_offset = None

    def render(self, surface):
        for i, item in enumerate(self.items):
            x = 50 + (i % 5) * 60
            y = 50 + (i // 5) * 60
            surface.blit(item.icon, (x, y))

            if item.quantity > 1:
                font = pygame.font.SysFont('Arial', 12)
                qty_text = font.render(str(item.quantity), True, (255, 255, 255))
                surface.blit(qty_text, (x + 20, y + 20))

        if self.selected_item and self.drag_offset:
            mouse_pos = pygame.mouse.get_pos()
            surface.blit(self.selected_item.icon,
                         (mouse_pos[0] - self.drag_offset[0],
                          mouse_pos[1] - self.drag_offset[1]))
