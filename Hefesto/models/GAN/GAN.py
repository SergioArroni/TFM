import torch
from torch import nn
from Hefesto.models.model import Model


class Generator(Model):
    def __init__(self, input_dim, hidden_dim, device):
        super().__init__(input_dim, hidden_dim, device=device)
        self.generator = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(True),
            nn.Linear(hidden_dim, hidden_dim * 2),
            nn.ReLU(True),
            nn.Linear(hidden_dim * 2, hidden_dim * 4),
            nn.ReLU(True),
            nn.Linear(hidden_dim * 4, hidden_dim * 8),
            nn.ReLU(True),
            nn.Linear(hidden_dim * 8, input_dim),
            nn.Sigmoid(),
        )

    def forward(self, x):
        return self.generator(x)

    def __str__(self):
        return "Generator"


class Discriminator(Model):
    def __init__(self, input_dim, hidden_dim, device):
        super().__init__(input_dim, hidden_dim, device=device)

        self.discriminator = nn.Sequential(
            nn.Linear(input_dim, hidden_dim * 4),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(hidden_dim * 4, hidden_dim * 2),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, x):
        return self.discriminator(x)

    # def train_model(self, input, optimizer_gen, optimizer_disc) -> torch.Tensor:
    #     batch_size = input.size(0)
    #     real_labels = torch.ones(batch_size, 1, device=input.device)
    #     fake_labels = torch.zeros(batch_size, 1, device=input.device)

    #     ### Entrenamiento del Discriminador ###
    #     optimizer_disc.zero_grad()

    #     # Real
    #     real_output = self.discriminator(input)
    #     d_loss_real = self.loss_fn(real_output, real_labels)

    #     # Falso
    #     z = torch.randn(batch_size, self.input_dim, device=input.device)
    #     fake_images = self.generator(z)
    #     fake_output = self.discriminator(fake_images.detach())
    #     d_loss_fake = self.loss_fn(fake_output, fake_labels)

    #     # Combinar pérdidas
    #     d_loss = d_loss_real + d_loss_fake
    #     d_loss.backward()
    #     optimizer_disc.step()

    #     ### Entrenamiento del Generador ###
    #     optimizer_gen.zero_grad()

    #     # Generar imágenes falsas para el entrenamiento del generador
    #     z = torch.randn(batch_size, self.input_dim, device=input.device)
    #     fake_images = self.generator(z)
    #     fake_output = self.discriminator(fake_images)
    #     g_loss = self.loss_fn(fake_output, real_labels)

    #     g_loss.backward()
    #     optimizer_gen.step()

    #     return d_loss + g_loss

    def __str__(self):
        return "Discriminator"


class GANModel(Model):
    def __init__(self, input_dim, hidden_dim, device):
        super().__init__(input_dim, hidden_dim, device=device)
        lr = 0.00001

        self.generator = Generator(input_dim, hidden_dim, device)
        self.gen_opt = torch.optim.Adam(self.generator.parameters(), lr=lr)

        self.discriminator = Discriminator(input_dim, hidden_dim, device)
        self.disc_opt = torch.optim.Adam(self.discriminator.parameters(), lr=lr)

    def forward(self, x):
        raise NotImplementedError("This method is not implemented")

    def get_noise(self, n_samples, noise_vector_dimension, device="cpu"):
        return torch.randn(n_samples, noise_vector_dimension, device=device)

    def get_disc_loss(
        self, gen, disc, criterion, real, num_images, noise_dimension, device
    ):
        # Generate noise and pass to generator
        fake_noise = self.get_noise(num_images, noise_dimension, device=device)
        fake = gen(fake_noise)

        # Pass fake features to discriminator
        # All of them will got label as 0
        # .detach() here is to ensure that only discriminator parameters will get update
        disc_fake_pred = disc(fake.detach())
        disc_fake_loss = criterion(disc_fake_pred, torch.zeros_like(disc_fake_pred))

        # Pass real features to discriminator
        # All of them will got label as 1
        disc_real_pred = disc(real)
        disc_real_loss = criterion(disc_real_pred, torch.ones_like(disc_real_pred))

        # Average of loss from both real and fake features
        disc_loss = (disc_fake_loss + disc_real_loss) / 2
        return disc_loss

    def get_gen_loss(self, gen, disc, criterion, num_images, noise_dimension, device):
        # Generate noise and pass to generator
        fake_noise = self.get_noise(num_images, noise_dimension, device=device)
        fake = gen(fake_noise)

        # Pass fake features to discriminator
        # But all of them will got label as 1
        disc_fake_pred = disc(fake)
        gen_loss = criterion(disc_fake_pred, torch.ones_like(disc_fake_pred))
        return gen_loss

    def train_model(self, model, input, optimizer, train=True):
        if train:
            model.train()
            optimizer.zero_grad()
        else:
            model.eval()
            
        # Paso 1: Entrenar el Discriminador con datos reales y falsos
        if train:
            self.disc_opt.zero_grad()

        # 1.1 Entrenamiento con datos reales
        real_pred = self.discriminator(input)
        real_loss = self.loss_fn(real_pred, torch.ones_like(real_pred))

        # 1.2 Entrenamiento con datos falsos generados
        noise = self.get_noise(input.size(0), self.input_dim, self.device)
        fake_data = self.generator(noise)
        fake_pred = self.discriminator(fake_data.detach())
        fake_loss = self.loss_fn(fake_pred, torch.zeros_like(fake_pred))

        # 1.3 Actualizar Discriminador
        disc_loss = (real_loss + fake_loss) / 2
        disc_loss.backward()
        self.disc_opt.step()

        # Paso 2: Entrenar el Generador (mejorar la falsificación)
        self.gen_opt.zero_grad()

        # 2.1 Generar datos falsos y evaluarlos
        fake_data = self.generator(
            noise
        )  # Reutilizamos el mismo ruido generado anteriormente
        tricked_pred = self.discriminator(fake_data)
        gen_loss = self.loss_fn(tricked_pred, torch.ones_like(tricked_pred))

        # 2.2 Actualizar Generador
        gen_loss.backward()
        self.gen_opt.step()

        return disc_loss.item(), gen_loss.item()

    def __str__(self):
        return "GANModel"
