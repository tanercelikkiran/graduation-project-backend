from typing import List, TypeVar, Generic, Union, Literal, Optional  # Optional eklendi
from bson import ObjectId
from pydantic import BaseModel, Field  # Field eklendi
from datetime import datetime  # datetime eklendi


class PyramidOptionsBase(BaseModel):
    sentence: str  # Bu, AI tarafından üretilen değiştirilmiş/genişletilmiş/daraltılmış vb. cümledir.
    meaning: str


class PyramidShrinkOptions(PyramidOptionsBase):
    removed_word: str


class PyramidExpandOptions(PyramidOptionsBase):
    expand_word: str


class PyramidReplaceOptions(PyramidOptionsBase):
    # `sentence` alanı PyramidOptionsBase'den miras alınır ve değiştirilmiş cümleyi tutar.
    changed_word: str  # Değiştirilen yeni kelime
    replaced_word: str  # Orijinal cümleden değiştirilen kelime


class PyramidParaphOptions(
    BaseModel
):  # PyramidOptionsBase'den miras almıyor, çünkü 'sentence' alanı kafa karıştırıcı olabilir.
    paraphrased_sentence: str  # Bu, yeniden ifade edilmiş cümlenin kendisidir.
    meaning: str


# T, PyramidItemBase'deki options listesinin tipini belirtir.
# PyramidOptionsBase'den türeyen veya benzer bir yapıya sahip olmalı.
# PyramidParaphOptions farklı olduğu için T'yi Union olarak güncelleyebiliriz.
PyramidOptionConcreteTypes = Union[
    PyramidShrinkOptions,
    PyramidExpandOptions,
    PyramidReplaceOptions,
    PyramidParaphOptions,
]
T = TypeVar("T", bound=PyramidOptionConcreteTypes)


class PyramidItemBase(BaseModel, Generic[T]):
    step_type: str  # Bu genel bir string, alt sınıflar Literal kullanacak
    initial_sentence: str
    initial_sentence_meaning: str
    options: List[T]
    selected_option: Optional[int] = None  # Kullanıcının seçtiği opsiyonun indeksi
    selected_sentence: Optional[str] = None  # Seçilen opsiyona karşılık gelen cümle
    option_words: List[str] = Field(
        default_factory=list
    )  # Affected sentence elements to avoid repetition


# Literal step_type kullanan özelleşmiş sınıflar
class PyramidShrinkItem(PyramidItemBase[PyramidShrinkOptions]):
    step_type: Literal["shrink"] = "shrink"


class PyramidExpandItem(PyramidItemBase[PyramidExpandOptions]):
    step_type: Literal["expand"] = "expand"


class PyramidReplaceItem(PyramidItemBase[PyramidReplaceOptions]):
    step_type: Literal["replace"] = "replace"


class PyramidParaphItem(
    PyramidItemBase[PyramidParaphOptions]
):  # T burada PyramidParaphOptions olacak
    step_type: Literal["paraphrase"] = "paraphrase"


# Tüm piramit adımları için Union tipi
PyramidItem = Union[
    PyramidExpandItem, PyramidShrinkItem, PyramidReplaceItem, PyramidParaphItem
]


# Veritabanı ve ana iş mantığı için kullanılacak model
class Pyramid(BaseModel):
    id: str = Field(..., alias="_id")  # MongoDB _id alanı için alias
    user_id: str
    step_types: List[str]
    steps: List[PyramidItem]
    total_steps: int
    last_step: int  # 0-indexed
    completed: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        populate_by_name = True  # Alias'ların çalışması için
        json_encoders = {
            ObjectId: str
        }  # ObjectId'nin str'ye çevrilmesi için (eğer ObjectId direkt modelde kullanılırsa)


# API çıktısı için model (DB'den gelen _id'yi id olarak sunar)
class PyramidOut(BaseModel):
    id: str
    step_types: List[str]
    steps: List[PyramidItem]  # Adımlar artık seçilen opsiyonu da içerebilir
    total_steps: int
    last_step: int
    completed: bool = False
    # İstenirse created_at, updated_at da eklenebilir


# Bu model artık doğrudan Pyramid modeli içinde ele alındığı için gereksiz olabilir.
# class PyramidIn(Pyramid): # DB'ye yazılacak model için _id yerine id alabilir
#     pass


# Bu model de PyramidItemBase'deki selected_option/selected_sentence ile yönetildiği için
# ayrı bir PyramidUpdate modeli gerekmeyebilir.
# class PyramidUpdate(BaseModel):
#     id: str
#     # new_step: PyramidItem # Artık direkt adıma ekleniyor
#     last_step: int # Bu bilgi zaten piramidin kendisinde var
#     # selected_option: int
#     # selected_sentence: str
